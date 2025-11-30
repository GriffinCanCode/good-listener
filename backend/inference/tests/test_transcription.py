"""Tests for TranscriptionService."""

from unittest.mock import MagicMock, patch

import numpy as np


class TestTranscriptionService:
    """Tests for Whisper transcription."""

    def test_init(self, mock_whisper_model):
        """TranscriptionService initializes Whisper model."""
        with patch("app.services.audio.transcription.WhisperModel", return_value=mock_whisper_model):
            from app.services.audio.transcription import TranscriptionService

            service = TranscriptionService(model_size="tiny", device="cpu")
            assert service.model is not None

    def test_transcribe_success(self, mock_whisper_model):
        """transcribe returns text from audio."""
        with patch("app.services.audio.transcription.WhisperModel", return_value=mock_whisper_model):
            from app.services.audio.transcription import TranscriptionService

            service = TranscriptionService()

            audio = np.zeros(16000, dtype=np.float32)
            text, confidence = service.transcribe(audio)

            assert text == "Hello, this is a test."
            mock_whisper_model.transcribe.assert_called_once()

    def test_transcribe_with_language(self, mock_whisper_model):
        """transcribe passes language hint."""
        with patch("app.services.audio.transcription.WhisperModel", return_value=mock_whisper_model):
            from app.services.audio.transcription import TranscriptionService

            service = TranscriptionService()

            audio = np.zeros(16000, dtype=np.float32)
            service.transcribe(audio, language="en")

            call_kwargs = mock_whisper_model.transcribe.call_args.kwargs
            assert call_kwargs.get("language") == "en"

    def test_transcribe_empty_result(self):
        """transcribe handles empty segments."""
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=([], MagicMock()))

        with patch("app.services.audio.transcription.WhisperModel", return_value=mock_model):
            from app.services.audio.transcription import TranscriptionService

            service = TranscriptionService()

            audio = np.zeros(16000, dtype=np.float32)
            text, _ = service.transcribe(audio)

            assert text == ""


class TestVADService:
    """Tests for Silero VAD."""

    def test_init(self, mock_vad_model):
        """VADService initializes Silero model."""
        with patch("torch.hub.load", return_value=(mock_vad_model, None)):
            from app.services.audio.vad import VADService

            service = VADService(threshold=0.5)
            assert service.model is not None
            assert service.threshold == 0.5

    def test_detect_speech_positive(self, mock_vad_model):
        """detect_speech returns True for speech."""
        mock_vad_model.return_value = MagicMock(item=MagicMock(return_value=0.8))

        with patch("torch.hub.load", return_value=(mock_vad_model, None)):
            from app.services.audio.vad import VADService

            service = VADService(threshold=0.5)

            audio = np.zeros(512, dtype=np.float32)
            prob, is_speech = service.detect_speech(audio)

            assert prob == 0.8
            assert is_speech is True

    def test_detect_speech_negative(self, mock_vad_model):
        """detect_speech returns False for silence."""
        mock_vad_model.return_value = MagicMock(item=MagicMock(return_value=0.1))

        with patch("torch.hub.load", return_value=(mock_vad_model, None)):
            from app.services.audio.vad import VADService

            service = VADService(threshold=0.5)

            audio = np.zeros(512, dtype=np.float32)
            prob, is_speech = service.detect_speech(audio)

            assert prob == 0.1
            assert is_speech is False

    def test_reset_state(self, mock_vad_model):
        """reset_state calls model reset."""
        with patch("torch.hub.load", return_value=(mock_vad_model, None)):
            from app.services.audio.vad import VADService

            service = VADService()

            service.reset_state()

            mock_vad_model.reset_states.assert_called()
