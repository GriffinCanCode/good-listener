"""Silero VAD (Voice Activity Detection) service."""

import numpy as np
import torch

from app.core import get_logger

logger = get_logger(__name__)


class VADService:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.model, _ = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True)
        self.model.reset_states()
        logger.info(f"VADService initialized: threshold={threshold}")

    def detect_speech(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> tuple[float, bool]:
        """
        Detect speech in audio chunk.
        
        Args:
            audio_chunk: Float32 PCM audio (512 samples recommended)
            sample_rate: Sample rate (default 16000)
            
        Returns:
            Tuple of (speech_probability, is_speech)
        """
        tensor = torch.tensor(audio_chunk, dtype=torch.float32)
        prob = self.model(tensor, sample_rate).item()
        return prob, prob > self.threshold

    def reset_state(self) -> None:
        """Reset VAD model internal state."""
        self.model.reset_states()

