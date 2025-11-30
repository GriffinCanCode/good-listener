"""Tests for DiarizationService."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.audio.diarization import DiarizationService, SpeakerSegment


class TestDiarizationService:
    """Tests for speaker diarization."""

    def test_init(self, mock_diarization_pipeline):
        """DiarizationService initializes pyannote pipeline."""
        with patch("app.services.audio.diarization.Pipeline.from_pretrained", return_value=mock_diarization_pipeline):
            service = DiarizationService(device="cpu", auth_token="test-token")
            assert service.pipeline is not None

    def test_diarize_single_speaker(self, mock_diarization_pipeline):
        """diarize returns segments for single speaker."""
        with patch("app.services.audio.diarization.Pipeline.from_pretrained", return_value=mock_diarization_pipeline):
            service = DiarizationService()
            audio = np.zeros(16000 * 5, dtype=np.float32)
            segments = service.diarize(audio)

            assert len(segments) == 2
            assert segments[0].speaker == "SPEAKER_00"
            assert segments[0].start == 0.0
            assert segments[0].end == 2.5

    def test_diarize_multiple_speakers(self, mock_diarization_pipeline_multi):
        """diarize handles multiple speakers."""
        with patch("app.services.audio.diarization.Pipeline.from_pretrained", return_value=mock_diarization_pipeline_multi):
            service = DiarizationService()
            audio = np.zeros(16000 * 10, dtype=np.float32)
            segments = service.diarize(audio, min_speakers=2, max_speakers=3)

            speakers = {s.speaker for s in segments}
            assert len(speakers) >= 2

    def test_diarize_empty_audio(self, mock_diarization_pipeline_empty):
        """diarize handles empty/silent audio."""
        with patch("app.services.audio.diarization.Pipeline.from_pretrained", return_value=mock_diarization_pipeline_empty):
            service = DiarizationService()
            audio = np.zeros(16000, dtype=np.float32)
            segments = service.diarize(audio)

            assert segments == []

    def test_speaker_segment_immutable(self):
        """SpeakerSegment is immutable dataclass."""
        segment = SpeakerSegment(speaker="SPEAKER_00", start=0.0, end=1.0)
        assert segment.speaker == "SPEAKER_00"
        assert segment.start == 0.0
        assert segment.end == 1.0

        with pytest.raises(AttributeError):
            segment.speaker = "SPEAKER_01"
