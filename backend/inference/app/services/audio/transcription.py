"""Whisper-based speech-to-text transcription service."""

import numpy as np

import app.pb.cognition_pb2 as pb
from app.core import TranscriptionError, get_logger
from app.services.constants import WHISPER_BEAM_SIZE

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"):
        self._model_size, self._device, self._compute_type = model_size, device, compute_type
        self._model = None

    @property
    def model(self):
        """Lazy-load Whisper model on first use."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)
                logger.info(f"TranscriptionService initialized: model={self._model_size}, device={self._device}")
            except Exception as e:
                raise TranscriptionError("Failed to load Whisper model", code=pb.AUDIO_MODEL_LOAD_FAILED, cause=e) from e
        return self._model

    def transcribe(self, audio_data: np.ndarray, language: str | None = None) -> tuple[str, float]:
        """Transcribe audio to text. Args: audio_data (Float32 PCM @ 16kHz), language (optional hint). Returns: (text, confidence)."""
        if audio_data.size == 0:
            raise TranscriptionError("Empty audio input", code=pb.AUDIO_EMPTY_INPUT)
        try:
            kwargs = {"beam_size": WHISPER_BEAM_SIZE, **({"language": language} if language else {})}
            segments, info = self.model.transcribe(audio_data.ravel().astype(np.float32, copy=False), **kwargs)
            return " ".join(s.text for s in segments).strip(), getattr(info, "language_probability", 1.0)
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError("Transcription failed", code=pb.AUDIO_TRANSCRIPTION_FAILED, cause=e) from e
