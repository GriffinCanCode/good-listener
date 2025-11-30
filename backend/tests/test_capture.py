"""Tests for CaptureService."""
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image


class TestCaptureService:
    """Tests for screen capture functionality."""

    def test_init(self, mock_mss):
        """CaptureService initializes mss correctly."""
        from app.services.capture import CaptureService
        
        service = CaptureService()
        assert service.sct is not None

    def test_capture_screen_success(self, mock_mss):
        """capture_screen returns PIL Image on success."""
        from app.services.capture import CaptureService
        
        with patch('app.services.capture.mss.mss', return_value=mock_mss):
            service = CaptureService()
            service.sct = mock_mss
            
            result = service.capture_screen(monitor_index=1)
            
            assert result is not None
            assert isinstance(result, Image.Image)
            mock_mss.grab.assert_called_once()

    def test_capture_screen_invalid_monitor(self, mock_mss):
        """capture_screen returns None for invalid monitor index."""
        from app.services.capture import CaptureService
        
        with patch('app.services.capture.mss.mss', return_value=mock_mss):
            service = CaptureService()
            service.sct = mock_mss
            
            # monitors list has 2 items, index 5 is invalid
            result = service.capture_screen(monitor_index=5)
            
            assert result is None

    def test_capture_screen_default_monitor(self, mock_mss):
        """capture_screen uses monitor index 1 by default."""
        from app.services.capture import CaptureService
        
        with patch('app.services.capture.mss.mss', return_value=mock_mss):
            service = CaptureService()
            service.sct = mock_mss
            
            service.capture_screen()
            
            # Should grab monitor at index 1 (primary monitor)
            mock_mss.grab.assert_called_with(mock_mss.monitors[1])

    def test_capture_screen_exception(self, mock_mss):
        """capture_screen handles exceptions gracefully."""
        from app.services.capture import CaptureService
        
        with patch('app.services.capture.mss.mss', return_value=mock_mss):
            service = CaptureService()
            service.sct = mock_mss
            mock_mss.grab.side_effect = Exception("Capture failed")
            
            result = service.capture_screen()
            
            assert result is None

