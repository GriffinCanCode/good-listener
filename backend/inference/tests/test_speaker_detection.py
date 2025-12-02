"""Tests for SpeakerDetectionService."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.audio.speaker_detection import SpeakerDetectionService, SpeakerProfile


class TestSpeakerDetectionService:
    """Tests for fast speaker detection."""

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock pyannote Inference model."""
        model = MagicMock()
        # Return normalized embeddings
        model.return_value = MagicMock(cpu=lambda: MagicMock(numpy=lambda: MagicMock(flatten=lambda: np.array([0.6, 0.8]))))
        return model

    def test_init(self):
        """SpeakerDetectionService initializes without loading model."""
        service = SpeakerDetectionService(device="cpu")
        assert service._model is None
        assert service._next_speaker_id == 0

    def test_detect_speaker_new_speaker(self, mock_embedding_model):
        """detect_speaker creates new speaker for first audio."""
        with patch("pyannote.audio.Inference", return_value=mock_embedding_model):
            service = SpeakerDetectionService()
            audio = np.random.randn(16000).astype(np.float32)  # 1 second
            
            speaker_id = service.detect_speaker(audio, sample_rate=16000, source="system")
            
            assert speaker_id == "Speaker 1"
            assert service.get_speaker_count("system") == 1

    def test_detect_speaker_same_speaker(self, mock_embedding_model):
        """detect_speaker recognizes same speaker with similar embedding."""
        with patch("pyannote.audio.Inference", return_value=mock_embedding_model):
            service = SpeakerDetectionService()
            audio1 = np.random.randn(16000).astype(np.float32)
            audio2 = np.random.randn(16000).astype(np.float32)
            
            # Mock to return very similar embeddings
            embeddings = [
                np.array([0.6, 0.8]),
                np.array([0.62, 0.78])  # Very similar
            ]
            mock_embedding_model.side_effect = [
                MagicMock(cpu=lambda: MagicMock(numpy=lambda: MagicMock(flatten=lambda: e)))
                for e in embeddings
            ]
            
            speaker1 = service.detect_speaker(audio1, source="system")
            speaker2 = service.detect_speaker(audio2, source="system")
            
            assert speaker1 == speaker2  # Same speaker detected
            assert service.get_speaker_count("system") == 1

    def test_detect_speaker_different_speakers(self):
        """detect_speaker creates new speaker for different embedding."""
        with patch("pyannote.audio.Inference") as mock_inference:
            service = SpeakerDetectionService()
            audio1 = np.random.randn(16000).astype(np.float32)
            audio2 = np.random.randn(16000).astype(np.float32)
            
            # Mock to return very different embeddings (orthogonal = cosine similarity ~0)
            def mock_call(audio_dict):
                # Return different embeddings based on call count
                if not hasattr(mock_call, 'count'):
                    mock_call.count = 0
                mock_call.count += 1
                
                if mock_call.count == 1:
                    embedding = np.array([1.0, 0.0])
                else:
                    embedding = np.array([0.0, 1.0])
                
                result = MagicMock()
                result.cpu.return_value.numpy.return_value.flatten.return_value = embedding
                return result
            
            mock_inference.return_value = mock_call
            
            speaker1 = service.detect_speaker(audio1, source="system")
            speaker2 = service.detect_speaker(audio2, source="system")
            
            assert speaker1 == "Speaker 1"
            assert speaker2 == "Speaker 2"
            assert service.get_speaker_count("system") == 2

    def test_detect_speaker_multiple_sources(self, mock_embedding_model):
        """detect_speaker tracks speakers separately per source."""
        with patch("pyannote.audio.Inference", return_value=mock_embedding_model):
            service = SpeakerDetectionService()
            audio = np.random.randn(16000).astype(np.float32)
            
            speaker1 = service.detect_speaker(audio, source="system")
            speaker2 = service.detect_speaker(audio, source="user")
            
            assert speaker1 == "Speaker 1"
            assert speaker2 == "Speaker 2"  # Different source = new speaker
            assert service.get_speaker_count("system") == 1
            assert service.get_speaker_count("user") == 1
            assert service.get_speaker_count() == 2

    def test_detect_speaker_short_audio(self, mock_embedding_model):
        """detect_speaker handles short audio gracefully."""
        with patch("pyannote.audio.Inference", return_value=mock_embedding_model):
            service = SpeakerDetectionService()
            short_audio = np.random.randn(1000).astype(np.float32)  # 0.0625 seconds
            
            # Should return default for short audio
            speaker_id = service.detect_speaker(short_audio, source="system")
            assert speaker_id == "Speaker 1"

    def test_reset_all(self, mock_embedding_model):
        """reset clears all speaker profiles."""
        with patch("pyannote.audio.Inference", return_value=mock_embedding_model):
            service = SpeakerDetectionService()
            audio = np.random.randn(16000).astype(np.float32)
            
            service.detect_speaker(audio, source="system")
            assert service.get_speaker_count() == 1
            
            service.reset()
            assert service.get_speaker_count() == 0
            assert service._next_speaker_id == 0

    def test_reset_source(self, mock_embedding_model):
        """reset clears speakers for specific source only."""
        with patch("pyannote.audio.Inference", return_value=mock_embedding_model):
            service = SpeakerDetectionService()
            audio = np.random.randn(16000).astype(np.float32)
            
            service.detect_speaker(audio, source="system")
            service.detect_speaker(audio, source="user")
            assert service.get_speaker_count() == 2
            
            service.reset(source="system")
            assert service.get_speaker_count("system") == 0
            assert service.get_speaker_count("user") == 1

    def test_speaker_profile_immutable(self):
        """SpeakerProfile is immutable dataclass."""
        profile = SpeakerProfile(
            speaker_id="Speaker 1",
            embedding=np.array([0.6, 0.8]),
            sample_count=5
        )
        assert profile.speaker_id == "Speaker 1"
        assert profile.sample_count == 5
        
        with pytest.raises(AttributeError):
            profile.speaker_id = "Speaker 2"

