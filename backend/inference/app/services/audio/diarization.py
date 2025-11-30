"""Speaker diarization service using pyannote-audio."""

from dataclasses import dataclass

import numpy as np

import app.pb.cognition_pb2 as pb
from app.core import DiarizationError, get_logger
from app.services.constants import DIARIZATION_MIN_SPEAKERS, DIARIZATION_MODEL

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SpeakerSegment:
    """A speaker segment with timing and label."""

    speaker: str
    start: float
    end: float


class DiarizationService:
    """Speaker diarization using pyannote-audio."""

    def __init__(self, model: str = DIARIZATION_MODEL, device: str = "cpu", auth_token: str | None = None):
        self.model_name = model
        self.device_name = device
        self.auth_token = auth_token
        self._pipeline = None
        self._torch = None

    @property
    def pipeline(self):
        """Lazy-load Pyannote pipeline on first use."""
        if self._pipeline is None:
            try:
                import torch
                from pyannote.audio import Pipeline

                self._torch = torch
                self.device = torch.device(self.device_name)
                self._pipeline = Pipeline.from_pretrained(self.model_name, token=self.auth_token)
                self._pipeline.to(self.device)
                logger.info(f"DiarizationService initialized: model={self.model_name}, device={self.device_name}")
            except Exception as e:
                raise DiarizationError("Failed to load diarization model", code=pb.AUDIO_MODEL_LOAD_FAILED, cause=e) from e
        return self._pipeline

    def diarize(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        min_speakers: int = DIARIZATION_MIN_SPEAKERS,
        max_speakers: int | None = None,
    ) -> list[SpeakerSegment]:
        """Diarize audio to identify speaker segments."""
        if audio.size == 0:
            raise DiarizationError("Empty audio input", code=pb.AUDIO_EMPTY_INPUT)
        try:
            # Ensure pipeline is loaded
            pipeline = self.pipeline
            waveform = self._torch.tensor(audio.flatten(), dtype=self._torch.float32).unsqueeze(0)
            diarization = pipeline(
                {"waveform": waveform, "sample_rate": sample_rate},
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
            return [
                SpeakerSegment(speaker=speaker, start=segment.start, end=segment.end)
                for segment, _, speaker in diarization.itertracks(yield_label=True)
            ]
        except DiarizationError:
            raise
        except Exception as e:
            raise DiarizationError("Diarization failed", code=pb.AUDIO_DIARIZATION_FAILED, cause=e) from e

