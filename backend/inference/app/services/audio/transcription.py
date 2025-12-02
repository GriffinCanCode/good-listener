"""Whisper-based speech-to-text transcription service."""

import numpy as np

import app.pb.cognition_pb2 as pb
from app.core import TranscriptionError, get_logger
from app.services.constants import WHISPER_BEAM_SIZE

logger = get_logger(__name__)


def _detect_device() -> tuple[str, str]:
    """Detect best available device and compute type."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"


class TranscriptionService:
    def __init__(self, model_size: str = "base", device: str | None = None, compute_type: str | None = None):
        auto_device, auto_compute = _detect_device()
        self._args = {
            "model_size_or_path": model_size,
            "device": device or auto_device,
            "compute_type": compute_type or auto_compute,
            "cpu_threads": 4,
            "num_workers": 2,
        }
        self._model = None

    @property
    def model(self):
        if not self._model:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(**self._args)
                logger.info(f"TranscriptionService ready: {self._args}")
            except Exception as e:
                raise TranscriptionError("Model load failed", code=pb.AUDIO_MODEL_LOAD_FAILED, cause=e) from e
        return self._model

    def transcribe(self, audio: np.ndarray, lang: str | None = "en") -> tuple[str, float]:
        if audio.size == 0:
            raise TranscriptionError("Empty audio", code=pb.AUDIO_EMPTY_INPUT)
        try:
            segments, info = self.model.transcribe(
                audio.ravel().astype(np.float32, copy=False),
                beam_size=WHISPER_BEAM_SIZE,
                language=lang,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                log_prob_threshold=-1.0,
            )
            return " ".join(s.text for s in segments).strip(), getattr(info, "language_probability", 1.0)
        except Exception as e:
            raise TranscriptionError("Transcription failed", code=pb.AUDIO_TRANSCRIPTION_FAILED, cause=e) from e
