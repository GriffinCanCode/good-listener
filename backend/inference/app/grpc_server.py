"""gRPC server exposing inference services to the Go platform."""

import asyncio
import io
import os
import re
from concurrent import futures

import grpc
import numpy as np
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from app.core import get_logger, TraceContext, set_trace_context, span, TracingInterceptor
from app.services.transcription import TranscriptionService
from app.services.vad import VADService
from app.services.ocr import OCRService
from app.services.llm import LLMService
from app.services.memory import MemoryService
import app.pb.cognition_pb2 as pb
import app.pb.cognition_pb2_grpc as pb_grpc

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
    if not text or len(text) < 10:
        return False
    return text.endswith("?") or bool(QUESTION_STARTERS.match(text))


class TranscriptionServicer(pb_grpc.TranscriptionServiceServicer):
    def __init__(self):
        self.service = TranscriptionService()

    def Transcribe(self, request: pb.TranscribeRequest, context) -> pb.TranscribeResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        with span("transcribe", audio_len=len(request.audio_data)):
            audio = np.frombuffer(request.audio_data, dtype=np.float32)
            text, confidence = self.service.transcribe(audio, request.language or None)
            return pb.TranscribeResponse(text=text, confidence=confidence, duration_ms=int(len(audio) / 16))

    def StreamTranscribe(self, request_iterator, context):
        """Stream transcription - accumulates chunks and transcribes on silence."""
        buffer = []
        for chunk in request_iterator:
            audio = np.frombuffer(chunk.data, dtype=np.float32)
            buffer.extend(audio.tolist())
            
            # Yield partial results when buffer is large enough
            if len(buffer) >= 16000:  # 1 second
                text, _ = self.service.transcribe(np.array(buffer))
                if text:
                    yield pb.TranscriptSegment(
                        text=text, 
                        device_id=chunk.device_id,
                        is_final=False,
                    )
                buffer = []


class VADServicer(pb_grpc.VADServiceServicer):
    def __init__(self):
        self.service = VADService()

    def DetectSpeech(self, request: pb.VADRequest, context) -> pb.VADResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        audio = np.frombuffer(request.audio_chunk, dtype=np.float32)
        prob, is_speech = self.service.detect_speech(audio, request.sample_rate or 16000)
        return pb.VADResponse(speech_probability=prob, is_speech=is_speech)

    def ResetState(self, request: pb.ResetStateRequest, context) -> pb.ResetStateResponse:
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
                    coords = [int(x) for x in line[1:coords_end-1].split(", ")]
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
            context_parts.append(f"SCREEN TEXT:\n{request.context_text[:2000]}")
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


class MemoryServicer(pb_grpc.MemoryServiceServicer):
    def __init__(self, memory_service: MemoryService):
        self.service = memory_service

    def Store(self, request: pb.StoreRequest, context) -> pb.StoreResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        metadata = dict(request.metadata) if request.metadata else None
        self.service.add_memory(request.text, request.source, metadata)
        return pb.StoreResponse(success=True)

    def Query(self, request: pb.QueryRequest, context) -> pb.QueryResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        filter_meta = {"source": request.source_filter} if request.source_filter else None
        docs = self.service.query_memory(request.query_text, request.n_results or 5, filter_meta)
        return pb.QueryResponse(documents=docs)

    def Clear(self, request: pb.ClearRequest, context) -> pb.ClearResponse:
        ctx = TraceContext.from_grpc_context(context)
        set_trace_context(ctx)
        return pb.ClearResponse(deleted_count=0)


async def serve(port: int = 50051):
    """Start the gRPC server."""
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[TracingInterceptor()],
    )
    
    memory_service = MemoryService()
    
    pb_grpc.add_TranscriptionServiceServicer_to_server(TranscriptionServicer(), server)
    pb_grpc.add_VADServiceServicer_to_server(VADServicer(), server)
    pb_grpc.add_OCRServiceServicer_to_server(OCRServicer(), server)
    pb_grpc.add_LLMServiceServicer_to_server(LLMServicer(memory_service), server)
    pb_grpc.add_MemoryServiceServicer_to_server(MemoryServicer(memory_service), server)
    
    addr = f"[::]:{port}"
    server.add_insecure_port(addr)
    
    logger.info(f"Inference gRPC server starting on {addr}")
    await server.start()
    await server.wait_for_termination()


def main():
    port = int(os.getenv("GRPC_PORT", "50051"))
    asyncio.run(serve(port))


if __name__ == "__main__":
    main()

