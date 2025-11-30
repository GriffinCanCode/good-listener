"""Whisper-based speech-to-text transcription service."""

import numpy as np
from faster_whisper import WhisperModel

from app.core import get_logger

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"TranscriptionService initialized: model={model_size}, device={device}")

    def transcribe(self, audio_data: np.ndarray, language: str | None = None) -> tuple[str, float]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Float32 PCM audio at 16kHz
            language: Optional language hint
            
        Returns:
            Tuple of (transcribed_text, confidence)
        """
        audio_data = audio_data.flatten().astype(np.float32)
        
        kwargs = {"beam_size": 1}  # Optimized for real-time
        if language:
            kwargs["language"] = language
            
        segments, info = self.model.transcribe(audio_data, **kwargs)
        text = " ".join(s.text for s in segments).strip()
        
        return text, getattr(info, "language_probability", 1.0)

