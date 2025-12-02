"""Fast speaker change detection using voice embeddings.

Uses lightweight speaker embeddings to detect when speakers change,
much faster than full diarization while maintaining good accuracy.
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np

import app.pb.cognition_pb2 as pb
from app.core import AudioError, get_logger
from app.services.constants import (
    SPEAKER_EMBEDDING_MODEL,
    SPEAKER_SIMILARITY_THRESHOLD,
    SPEAKER_MIN_AUDIO_LENGTH,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SpeakerProfile:
    """Cached speaker embedding profile."""
    
    speaker_id: str
    embedding: np.ndarray
    sample_count: int


class SpeakerDetectionService:
    """Fast speaker change detection using embeddings."""

    def __init__(self, model: str = SPEAKER_EMBEDDING_MODEL, device: str = "cpu"):
        self.model_name = model
        self.device_name = device
        self._model = None
        self._torch = None
        self._speakers: Dict[str, SpeakerProfile] = {}
        self._next_speaker_id = 0

    @property
    def model(self):
        """Lazy-load speaker embedding model."""
        if self._model is None:
            try:
                import torch
                from pyannote.audio import Inference
                
                self._torch = torch
                self.device = torch.device(self.device_name)
                self._model = Inference(self.model_name, device=self.device)
                logger.info(f"SpeakerDetectionService initialized: model={self.model_name}, device={self.device_name}")
            except Exception as e:
                raise AudioError(
                    "Failed to load speaker detection model",
                    code=pb.AUDIO_MODEL_LOAD_FAILED,
                    cause=e
                ) from e
        return self._model

    def detect_speaker(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        source: str = "system",
    ) -> str:
        """Detect which speaker is talking (fast embedding comparison).
        
        Args:
            audio: Audio samples as float32 numpy array
            sample_rate: Audio sample rate
            source: Audio source identifier for tracking speakers per source
            
        Returns:
            Speaker ID (e.g., "Speaker 1", "Speaker 2", etc.)
        """
        if audio.size == 0:
            raise AudioError("Empty audio input", code=pb.AUDIO_EMPTY_INPUT)
        
        # Skip if audio too short for reliable embedding
        if len(audio) < SPEAKER_MIN_AUDIO_LENGTH * sample_rate:
            return self._get_last_speaker(source)
        
        try:
            # Extract embedding
            embedding = self._extract_embedding(audio, sample_rate)
            
            # Find best matching speaker or create new one
            speaker_id = self._match_or_create_speaker(embedding, source)
            
            return speaker_id
            
        except Exception as e:
            logger.warning(f"Speaker detection failed: {e}")
            return self._get_last_speaker(source)

    def _extract_embedding(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract speaker embedding from audio (optimized for speed)."""
        model = self.model
        
        # Convert to torch tensor
        waveform = self._torch.from_numpy(audio.flatten()).float().unsqueeze(0)
        
        # Extract embedding (single forward pass, very fast)
        with self._torch.no_grad():
            embedding = model({"waveform": waveform, "sample_rate": sample_rate})
        
        # Normalize for cosine similarity
        embedding = embedding.cpu().numpy().flatten()
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding

    def _match_or_create_speaker(self, embedding: np.ndarray, source: str) -> str:
        """Match embedding to existing speaker or create new one."""
        best_match = None
        best_similarity = -1.0
        
        # Compare with existing speakers from this source
        source_speakers = {k: v for k, v in self._speakers.items() if k.startswith(f"{source}_")}
        
        for speaker_key, profile in source_speakers.items():
            # Cosine similarity (already normalized)
            similarity = np.dot(embedding, profile.embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = profile
        
        # Use existing speaker if similarity above threshold
        if best_match and best_similarity >= SPEAKER_SIMILARITY_THRESHOLD:
            # Update embedding with exponential moving average for robustness
            alpha = 0.3  # Weight for new embedding
            updated_embedding = alpha * embedding + (1 - alpha) * best_match.embedding
            updated_embedding = updated_embedding / (np.linalg.norm(updated_embedding) + 1e-8)
            
            speaker_key = f"{source}_{best_match.speaker_id}"
            self._speakers[speaker_key] = SpeakerProfile(
                speaker_id=best_match.speaker_id,
                embedding=updated_embedding,
                sample_count=best_match.sample_count + 1
            )
            
            return best_match.speaker_id
        
        # Create new speaker
        speaker_id = f"Speaker {self._next_speaker_id + 1}"
        speaker_key = f"{source}_{speaker_id}"
        self._speakers[speaker_key] = SpeakerProfile(
            speaker_id=speaker_id,
            embedding=embedding,
            sample_count=1
        )
        self._next_speaker_id += 1
        
        logger.info(f"New speaker detected: {speaker_id} (source: {source})")
        return speaker_id

    def _get_last_speaker(self, source: str) -> str:
        """Get the most recent speaker for this source."""
        source_speakers = [v for k, v in self._speakers.items() if k.startswith(f"{source}_")]
        if source_speakers:
            # Return most recently updated speaker
            return max(source_speakers, key=lambda s: s.sample_count).speaker_id
        return "Speaker 1"  # Default

    def reset(self, source: str | None = None):
        """Reset speaker profiles (optionally for specific source)."""
        if source:
            self._speakers = {k: v for k, v in self._speakers.items() if not k.startswith(f"{source}_")}
            logger.info(f"Reset speaker profiles for source: {source}")
        else:
            self._speakers.clear()
            self._next_speaker_id = 0
            logger.info("Reset all speaker profiles")

    def get_speaker_count(self, source: str | None = None) -> int:
        """Get number of detected speakers (optionally for specific source)."""
        if source:
            return len([k for k in self._speakers.keys() if k.startswith(f"{source}_")])
        return len(set(p.speaker_id for p in self._speakers.values()))

