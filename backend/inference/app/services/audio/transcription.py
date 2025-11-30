"""Whisper-based speech-to-text transcription service."""

import numpy as np
from faster_whisper import WhisperModel

from app.core import get_logger
from app.services.constants import WHISPER_BEAM_SIZE

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"TranscriptionService initialized: model={model_size}, device={device}")

    def transcribe(self, audio_data: np.ndarray, language: str | None = None) -> tuple[str, float]:
        """Transcribe audio to text. Args: audio_data (Float32 PCM @ 16kHz), language (optional hint). Returns: (text, confidence)."""
        kwargs = {"beam_size": WHISPER_BEAM_SIZE, **({"language": language} if language else {})}
        segments, info = self.model.transcribe(audio_data.flatten().astype(np.float32), **kwargs)
        return " ".join(s.text for s in segments).strip(), getattr(info, "language_probability", 1.0)
