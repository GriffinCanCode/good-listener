"""Silero VAD (Voice Activity Detection) service."""

import numpy as np

import app.pb.cognition_pb2 as pb
from app.core import VADError, get_logger
from app.services.constants import VAD_DEFAULT_SAMPLE_RATE, VAD_DEFAULT_THRESHOLD

logger = get_logger(__name__)


class VADService:
    def __init__(self, threshold: float = VAD_DEFAULT_THRESHOLD):
        self.threshold = threshold
        self._model = None
        self._torch = None

    @property
    def model(self):
        """Lazy-load VAD model on first use."""
        if self._model is None:
            try:
                import torch
                self._torch = torch
                self._model, _ = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True)
                self._model.reset_states()
                logger.info(f"VADService initialized: threshold={self.threshold}")
            except Exception as e:
                raise VADError("Failed to load VAD model", code=pb.AUDIO_MODEL_LOAD_FAILED, cause=e) from e
        return self._model

    def detect_speech(self, audio_chunk: np.ndarray, sample_rate: int = VAD_DEFAULT_SAMPLE_RATE) -> tuple[float, bool]:
        """Detect speech in audio chunk. Args: audio_chunk (Float32 PCM, 512 samples), sample_rate. Returns: (prob, is_speech)."""
        try:
            _ = self.model  # Ensure model is loaded (also loads torch)
            return (p := self._model(self._torch.tensor(audio_chunk, dtype=self._torch.float32), sample_rate).item()), p > self.threshold
        except VADError:
            raise
        except Exception as e:
            raise VADError("VAD detection failed", code=pb.AUDIO_VAD_FAILED, cause=e) from e

    def reset_state(self) -> None:
        """Reset VAD model internal state."""
        if self._model:
            self._model.reset_states()
