"""Speaker diarization service using pyannote-audio."""

from dataclasses import dataclass

import numpy as np
import torch
from pyannote.audio import Pipeline

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
        try:
            self.device = torch.device(device)
            self.pipeline = Pipeline.from_pretrained(model, use_auth_token=auth_token)
            self.pipeline.to(self.device)
            logger.info(f"DiarizationService initialized: model={model}, device={device}")
        except Exception as e:
            raise DiarizationError("Failed to load diarization model", code=pb.AUDIO_MODEL_LOAD_FAILED, cause=e) from e

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
            waveform = torch.tensor(audio.flatten(), dtype=torch.float32).unsqueeze(0)
            diarization = self.pipeline(
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

