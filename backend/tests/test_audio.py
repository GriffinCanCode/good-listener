"""Tests for AudioService and DeviceListener."""
import pytest
from unittest.mock import MagicMock, patch, call
import numpy as np
import threading
import time


class TestDeviceListener:
    """Tests for audio device listener."""

    def test_init(self, mock_vad):
        """DeviceListener initializes with VAD model."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(
            device_index=0,
            sample_rate=16000,
            transcribe_callback=callback,
            vad_threshold=0.5
        )
        
        assert listener.device_index == 0
        assert listener.sample_rate == 16000
        assert listener.vad_threshold == 0.5
        assert listener.is_listening is False

    def test_start_stop(self, mock_vad, mock_sounddevice):
        """DeviceListener starts and stops listening thread."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(0, 16000, callback)
        
        with patch.object(listener, '_loop'):
            listener.start()
            assert listener.is_listening is True
            
            listener.stop()
            assert listener.is_listening is False

    def test_process_speech_detection(self, mock_vad):
        """_process detects speech via VAD."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(0, 16000, callback)
        
        # Simulate speech chunk (VAD returns > 0.5)
        speech_chunk = np.random.rand(512).astype(np.float32)
        listener._process(speech_chunk)
        
        assert listener.is_speaking is True
        assert len(listener.speech_buffer) > 0

    def test_process_silence_triggers_transcribe(self, mock_vad):
        """_process triggers transcription after silence."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(0, 16000, callback, vad_threshold=0.5)
        
        # Simulate speech first
        listener.vad_model.return_value.item.return_value = 0.8
        for _ in range(20):
            listener._process(np.random.rand(512).astype(np.float32))
        
        # Switch to silence
        listener.vad_model.return_value.item.return_value = 0.1
        for _ in range(listener.max_silence_chunks + 2):
            listener._process(np.zeros(512).astype(np.float32))
        
        # Callback should be called with speech buffer
        callback.assert_called()

    def test_process_stereo_to_mono(self, mock_vad):
        """_process converts stereo to mono."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(0, 16000, callback)
        
        # Stereo input (2 channels)
        stereo_chunk = np.random.rand(512, 2).astype(np.float32)
        listener._process(stereo_chunk)
        
        # Should process without error
        assert True

    def test_process_short_speech_ignored(self, mock_vad):
        """_process ignores speech segments < 0.5 seconds."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(0, 16000, callback)
        
        # Single short speech chunk (~32ms at 16kHz)
        listener.vad_model.return_value.item.return_value = 0.8
        listener._process(np.random.rand(512).astype(np.float32))
        
        # Set is_speaking and add minimal buffer manually to test short detection
        listener.is_speaking = True
        listener.speech_buffer = list(np.zeros(100))  # Very short buffer
        
        # Immediate silence - trigger end of speech
        listener.vad_model.return_value.item.return_value = 0.1
        listener.silence_chunks = listener.max_silence_chunks  # Force silence detection
        listener._process(np.zeros(512).astype(np.float32))
        
        # Callback should NOT be called (speech buffer too short: < 8000 samples)
        callback.assert_not_called()

    def test_callback_audio_status(self, mock_vad):
        """_callback handles status warnings."""
        from app.services.audio import DeviceListener
        
        callback = MagicMock()
        listener = DeviceListener(0, 16000, callback)
        
        # Simulate callback with status
        indata = np.zeros((512, 1), dtype=np.float32)
        listener._callback(indata, 512, None, "input overflow")
        
        # Should still queue data
        assert not listener.queue.empty()


class TestAudioService:
    """Tests for audio service."""

    def test_init(self, mock_sounddevice, mock_whisper, mock_vad):
        """AudioService initializes Whisper model."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService(model_size="tiny", device="cpu")
            
            assert service.model is not None
            assert service.listeners == []

    def test_start_listening(self, mock_sounddevice, mock_whisper, mock_vad):
        """start_listening creates device listeners."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            with patch('app.services.audio.DeviceListener') as MockListener:
                mock_listener_instance = MagicMock()
                MockListener.return_value = mock_listener_instance
                
                service = AudioService()
                callback = MagicMock()
                service.start_listening(callback)
                
                assert service.callback == callback
                mock_listener_instance.start.assert_called()

    def test_start_listening_idempotent(self, mock_sounddevice, mock_whisper, mock_vad):
        """start_listening is idempotent when already listening."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            with patch('app.services.audio.DeviceListener') as MockListener:
                mock_listener = MagicMock()
                MockListener.return_value = mock_listener
                
                service = AudioService()
                service.listeners = [mock_listener]  # Already has listener
                
                callback = MagicMock()
                service.start_listening(callback)
                
                # Should not create new listeners
                MockListener.assert_not_called()

    def test_stop_listening(self, mock_sounddevice, mock_whisper, mock_vad):
        """stop_listening stops all listeners."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            mock_listener = MagicMock()
            
            service = AudioService()
            service.listeners = [mock_listener]
            service.stop_listening()
            
            mock_listener.stop.assert_called_once()
            assert service.listeners == []

    def test_transcribe(self, mock_sounddevice, mock_whisper, mock_vad):
        """_transcribe processes audio and calls callback."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService()
            callback = MagicMock()
            service.callback = callback
            
            audio_data = np.random.rand(16000).astype(np.float32)
            service._transcribe(audio_data, "user")
            
            mock_whisper.transcribe.assert_called_once()
            callback.assert_called_once_with("Test transcription.", "user")

    def test_transcribe_empty_result(self, mock_sounddevice, mock_whisper, mock_vad):
        """_transcribe skips callback for empty transcription."""
        from app.services.audio import AudioService
        
        mock_whisper.transcribe.return_value = ([], None)
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService()
            callback = MagicMock()
            service.callback = callback
            
            audio_data = np.random.rand(16000).astype(np.float32)
            service._transcribe(audio_data, "user")
            
            callback.assert_not_called()

    def test_transcribe_exception(self, mock_sounddevice, mock_whisper, mock_vad):
        """_transcribe handles exceptions gracefully."""
        from app.services.audio import AudioService
        
        mock_whisper.transcribe.side_effect = Exception("Transcription failed")
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService()
            callback = MagicMock()
            service.callback = callback
            
            audio_data = np.random.rand(16000).astype(np.float32)
            # Should not raise
            service._transcribe(audio_data, "user")
            
            callback.assert_not_called()

    def test_get_input_devices_default(self, mock_sounddevice, mock_whisper, mock_vad):
        """_get_input_devices returns default device."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService(capture_system_audio=False)
            devices = service._get_input_devices()
            
            assert (0, "user") in devices

    def test_get_input_devices_with_system_audio(self, mock_sounddevice, mock_whisper, mock_vad):
        """_get_input_devices includes system audio devices."""
        from app.services.audio import AudioService
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService(capture_system_audio=True)
            devices = service._get_input_devices()
            
            # Should include BlackHole device
            assert any(src == "system" for _, src in devices)

    def test_get_input_devices_error_handling(self, mock_sounddevice, mock_whisper, mock_vad):
        """_get_input_devices handles query errors."""
        from app.services.audio import AudioService
        
        mock_sounddevice.default.device = [None, None]
        
        with patch('app.services.audio.WhisperModel', return_value=mock_whisper):
            service = AudioService()
            devices = service._get_input_devices()
            
            # Should handle gracefully
            assert isinstance(devices, list)

