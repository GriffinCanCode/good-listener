"""Silero VAD (Voice Activity Detection) service."""

import numpy as np
import torch

from app.core import get_logger
from app.services.constants import VAD_DEFAULT_SAMPLE_RATE, VAD_DEFAULT_THRESHOLD

logger = get_logger(__name__)


class VADService:
    def __init__(self, threshold: float = VAD_DEFAULT_THRESHOLD):
        self.threshold = threshold
        self.model, _ = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True)
        self.model.reset_states()
        logger.info(f"VADService initialized: threshold={threshold}")

    def detect_speech(self, audio_chunk: np.ndarray, sample_rate: int = VAD_DEFAULT_SAMPLE_RATE) -> tuple[float, bool]:
        """Detect speech in audio chunk. Args: audio_chunk (Float32 PCM, 512 samples), sample_rate. Returns: (prob, is_speech)."""
        return (p := self.model(torch.tensor(audio_chunk, dtype=torch.float32), sample_rate).item()), p > self.threshold

    def reset_state(self) -> None:
        """Reset VAD model internal state."""
        self.model.reset_states()
