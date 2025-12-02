"""Whisper-based speech-to-text transcription service."""

import numpy as np

import app.pb.cognition_pb2 as pb
from app.core import TranscriptionError, get_logger
from app.services.constants import WHISPER_BEAM_SIZE

logger = get_logger(__name__)


class TranscriptionService:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self._args = {"model_size_or_path": model_size, "device": device, "compute_type": compute_type}
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

    def transcribe(self, audio: np.ndarray, lang: str | None = None) -> tuple[str, float]:
        if audio.size == 0:
            raise TranscriptionError("Empty audio", code=pb.AUDIO_EMPTY_INPUT)
        try:
            segments, info = self.model.transcribe(
                audio.ravel().astype(np.float32, copy=False),
                beam_size=WHISPER_BEAM_SIZE,
                language=lang
            )
            return " ".join(s.text for s in segments).strip(), getattr(info, "language_probability", 1.0)
        except Exception as e:
            raise TranscriptionError("Transcription failed", code=pb.AUDIO_TRANSCRIPTION_FAILED, cause=e) from e
