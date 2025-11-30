"""gRPC server exposing inference services to the Go platform."""

import asyncio
import io
import os
import re
import signal
from concurrent import futures

import grpc
import numpy as np
from dotenv import load_dotenv
from grpc_health.v1 import health_pb2_grpc
from PIL import Image

load_dotenv()

import app.pb.cognition_pb2 as pb
import app.pb.cognition_pb2_grpc as pb_grpc
from app.core import TraceContext, TracingInterceptor, get_logger, set_trace_context, span
from app.services.constants import (
    DIARIZATION_MIN_SPEAKERS,
    GRPC_DEFAULT_PORT,
    GRPC_MAX_WORKERS,
    GRPC_SHUTDOWN_GRACE_PERIOD,
    MEMORY_QUERY_DEFAULT_RESULTS,
    MIN_QUESTION_LENGTH,
    SAMPLES_PER_SECOND,
    SCREEN_CONTEXT_MAX_LENGTH,
    VAD_DEFAULT_SAMPLE_RATE,
)
from app.services.audio import DiarizationService, TranscriptionService, VADService
from app.services.health import create_health_servicer
from app.services.llm import LLMService
from app.services.memory import MemoryService
from app.services.ocr import OCRService

logger = get_logger(__name__)

# Question detection pattern
QUESTION_STARTERS = re.compile(
    r"^(who|what|where|when|why|how|can|could|would|should|is|are|do|does|did|"
    r"have|has|will|won't|isn't|aren't|don't|doesn't|didn't|haven't|hasn't|"
    r"was|were|which|shall|may|might|tell me)\b",
    re.IGNORECASE,
)


def is_question(text: str) -> bool:
    """Detect if text is a question."""
    text = text.strip()
    if not text or len(text) < MIN_QUESTION_LENGTH:
        return False
    return text.endswith("?") or bool(QUESTION_STARTERS.match(text))


class TranscriptionServicer(pb_grpc.TranscriptionServiceServicer):
    def __init__(self, auth_token: str | None = None):
        self.service = TranscriptionService()
        self._diarization: DiarizationService | None = None
        self._auth_token = auth_token

    @property
    def diarization(self) -> DiarizationService:
        """Lazy-load diarization service (heavy model)."""
        if self._diarization is None:
            self._diarization = DiarizationService(auth_token=self._auth_token)
        return self._diarization

    def Transcribe(self, request: pb.TranscribeRequest, context) -> pb.TranscribeResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        with span("transcribe", audio_len=len(request.audio_data)):
            audio = np.frombuffer(request.audio_data, dtype=np.float32)
            text, confidence = self.service.transcribe(audio, request.language or None)
            duration_ms = int(len(audio) / (SAMPLES_PER_SECOND / 1000))
            return pb.TranscribeResponse(text=text, confidence=confidence, duration_ms=duration_ms)

    def StreamTranscribe(self, request_iterator, _context):
        """Stream transcription - accumulates chunks and transcribes on silence."""
        buffer = []
        for chunk in request_iterator:
            audio = np.frombuffer(chunk.data, dtype=np.float32)
            buffer.extend(audio.tolist())

            # Yield partial results when buffer is large enough (1 second of audio)
            if len(buffer) >= SAMPLES_PER_SECOND:
                text, _ = self.service.transcribe(np.array(buffer))
                if text:
                    yield pb.TranscriptSegment(
                        text=text,
                        device_id=chunk.device_id,
                        is_final=False,
                    )
                buffer = []

    def Diarize(self, request: pb.DiarizeRequest, context) -> pb.DiarizeResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        with span("diarize", audio_len=len(request.audio_data)):
            audio = np.frombuffer(request.audio_data, dtype=np.float32)
            sample_rate = request.sample_rate or SAMPLES_PER_SECOND
            min_speakers = request.min_speakers or DIARIZATION_MIN_SPEAKERS
            max_speakers = request.max_speakers if request.max_speakers > 0 else None
            segments = self.diarization.diarize(audio, sample_rate, min_speakers, max_speakers)
            return pb.DiarizeResponse(
                segments=[pb.SpeakerSegment(speaker=s.speaker, start_sec=s.start, end_sec=s.end) for s in segments]
            )


class VADServicer(pb_grpc.VADServiceServicer):
    def __init__(self):
        self.service = VADService()

    def DetectSpeech(self, request: pb.VADRequest, context) -> pb.VADResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        audio = np.frombuffer(request.audio_chunk, dtype=np.float32)
        prob, is_speech = self.service.detect_speech(audio, request.sample_rate or VAD_DEFAULT_SAMPLE_RATE)
        return pb.VADResponse(speech_probability=prob, is_speech=is_speech)

    def ResetState(self, _request: pb.ResetStateRequest, context) -> pb.ResetStateResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        self.service.reset_state()
        return pb.ResetStateResponse(success=True)


class OCRServicer(pb_grpc.OCRServiceServicer):
    def __init__(self):
        self.service = OCRService()

    def ExtractText(self, request: pb.OCRRequest, context) -> pb.OCRResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        with span("ocr_extract", image_size=len(request.image_data)):
            image = Image.open(io.BytesIO(request.image_data))
            text = self.service.extract_text(image)

        # Parse bounding boxes from OCR output format: [x1, y1, x2, y2] text
        boxes = []
        for line in text.split("\n"):
            if line.startswith("[") and "]" in line:
                try:
                    coords_end = line.index("]") + 1
                    coords = [int(x) for x in line[1 : coords_end - 1].split(", ")]
                    box_text = line[coords_end:].strip()
                    boxes.append(pb.BoundingBox(x1=coords[0], y1=coords[1], x2=coords[2], y2=coords[3], text=box_text))
                except (ValueError, IndexError):
                    pass

        return pb.OCRResponse(text=text, boxes=boxes)


class LLMServicer(pb_grpc.LLMServiceServicer):
    def __init__(self, memory_service: MemoryService):
        self.service = LLMService(
            provider=os.getenv("LLM_PROVIDER", "gemini"),
            model_name=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
            memory_service=memory_service,
        )

    async def Analyze(self, request: pb.AnalyzeRequest, context):
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        logger.info("llm_analyze_start", query_len=len(request.user_query))
        # Build context
        context_parts = []
        if request.transcript:
            context_parts.append(f"RECENT CONVERSATION:\n{request.transcript}")
        if request.context_text:
            context_parts.append(f"SCREEN TEXT:\n{request.context_text[:SCREEN_CONTEXT_MAX_LENGTH]}")
        context_text = "\n\n".join(context_parts) or "No context available."

        # Parse image if provided
        image = None
        if request.image_data:
            image = Image.open(io.BytesIO(request.image_data))

        async for chunk in self.service.analyze(context_text, request.user_query, image):
            yield pb.AnalyzeChunk(content=chunk, is_final=False)

        yield pb.AnalyzeChunk(content="", is_final=True)

    def IsQuestion(self, request: pb.IsQuestionRequest, context) -> pb.IsQuestionResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        return pb.IsQuestionResponse(is_question=is_question(request.text))

    async def SummarizeTranscript(self, request: pb.SummarizeRequest, context) -> pb.SummarizeResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        original_len = len(request.transcript)
        summary = await self.service.summarize(request.transcript, request.max_length)
        return pb.SummarizeResponse(summary=summary, original_length=original_len, summary_length=len(summary))


class MemoryServicer(pb_grpc.MemoryServiceServicer):
    def __init__(self, memory_service: MemoryService):
        self.service = memory_service

    def Store(self, request: pb.StoreRequest, context) -> pb.StoreResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        metadata = dict(request.metadata) if request.metadata else None
        doc_id = self.service.add_memory(request.text, request.source, metadata)
        return pb.StoreResponse(id=doc_id or "", success=doc_id is not None)

    def BatchStore(self, request: pb.BatchStoreRequest, context) -> pb.BatchStoreResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        items = [(item.text, item.source, dict(item.metadata) if item.metadata else None) for item in request.items]
        ids = self.service.add_memories_batch(items)
        return pb.BatchStoreResponse(ids=ids, stored_count=len(ids))

    def Query(self, request: pb.QueryRequest, context) -> pb.QueryResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        filter_meta = {"source": request.source_filter} if request.source_filter else None
        docs = self.service.query_memory(request.query_text, request.n_results or MEMORY_QUERY_DEFAULT_RESULTS, filter_meta)
        return pb.QueryResponse(documents=docs)

    def Clear(self, _request: pb.ClearRequest, context) -> pb.ClearResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        return pb.ClearResponse(deleted_count=0)


def _timed_load(name: str, loader):
    """Load a model/service and log duration."""
    import time
    start = time.perf_counter()
    result = loader()
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("model_loaded", name=name, duration_ms=round(elapsed_ms, 1))
    return result


async def serve(port: int = GRPC_DEFAULT_PORT):
    """Start the gRPC server with graceful shutdown."""
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=GRPC_MAX_WORKERS),
        interceptors=[TracingInterceptor()],
    )

    # Preload all ML models with timing
    logger.info("preloading_models")
    hf_token = os.getenv("HF_TOKEN")  # Hugging Face token for pyannote models
    memory_service = _timed_load("memory", MemoryService)
    transcription_servicer = _timed_load("transcription", lambda: TranscriptionServicer(auth_token=hf_token))
    vad_servicer = _timed_load("vad", VADServicer)
    ocr_servicer = _timed_load("ocr", OCRServicer)
    llm_servicer = _timed_load("llm", lambda: LLMServicer(memory_service))
    memory_servicer = MemoryServicer(memory_service)
    logger.info("models_preloaded")

    # Register services
    pb_grpc.add_TranscriptionServiceServicer_to_server(transcription_servicer, server)
    pb_grpc.add_VADServiceServicer_to_server(vad_servicer, server)
    pb_grpc.add_OCRServiceServicer_to_server(ocr_servicer, server)
    pb_grpc.add_LLMServiceServicer_to_server(llm_servicer, server)
    pb_grpc.add_MemoryServiceServicer_to_server(memory_servicer, server)

    # Register health check service with model availability checks
    health_servicer = create_health_servicer(
        transcription_svc=transcription_servicer.service,
        vad_svc=vad_servicer.service,
        ocr_svc=ocr_servicer.service,
        llm_svc=llm_servicer.service,
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    addr = f"[::]:{port}"
    server.add_insecure_port(addr)

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    def handle_shutdown(signum, _frame):
        sig_name = signal.Signals(signum).name
        logger.info("shutdown_signal_received", signal=sig_name)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("grpc_server_starting", addr=addr)
    await server.start()

    await shutdown_event.wait()
    logger.info("graceful_shutdown_initiated", grace_period=GRPC_SHUTDOWN_GRACE_PERIOD)
    await server.stop(grace=GRPC_SHUTDOWN_GRACE_PERIOD)
    logger.info("grpc_server_stopped")


def main():
    port = int(os.getenv("GRPC_PORT", str(GRPC_DEFAULT_PORT)))
    asyncio.run(serve(port))


if __name__ == "__main__":
    main()
