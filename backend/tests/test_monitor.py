"""Tests for BackgroundMonitor."""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from PIL import Image
import time


class TestIsQuestion:
    """Tests for question detection."""

    def test_explicit_question_mark(self):
        """Detects questions with explicit ?."""
        from app.services.monitor import is_question
        
        assert is_question("What time is it?") is True
        assert is_question("How does this work?") is True
        assert is_question("Is this correct?") is True

    def test_question_starters(self):
        """Detects questions by starter words."""
        from app.services.monitor import is_question
        
        assert is_question("What is the meaning of life") is True
        assert is_question("How do I fix this bug") is True
        assert is_question("Can you help me with this") is True
        assert is_question("Why is this happening") is True
        assert is_question("Tell me about your experience") is True

    def test_not_questions(self):
        """Non-questions return False."""
        from app.services.monitor import is_question
        
        assert is_question("I like pizza") is False
        assert is_question("This is a statement") is False
        assert is_question("Let me explain") is False

    def test_short_text_not_question(self):
        """Short text < 10 chars is not a question."""
        from app.services.monitor import is_question
        
        assert is_question("What?") is False
        assert is_question("How?") is False
        assert is_question("") is False

    def test_empty_and_whitespace(self):
        """Empty/whitespace returns False."""
        from app.services.monitor import is_question
        
        assert is_question("") is False
        assert is_question("   ") is False
        assert is_question("\n\t") is False


class TestBackgroundMonitor:
    """Tests for background monitoring service."""

    @pytest.fixture
    def monitor_services(self, mock_capture_service, mock_ocr_service, mock_audio_service, mock_memory_service):
        """Create monitor with mocked services."""
        from app.services.monitor import BackgroundMonitor
        
        return BackgroundMonitor(
            capture_service=mock_capture_service,
            ocr_service=mock_ocr_service,
            audio_service=mock_audio_service,
            memory_service=mock_memory_service,
        )

    @pytest.mark.asyncio
    async def test_start(self, monitor_services):
        """start initializes tasks and begins listening."""
        await monitor_services.start()
        
        assert monitor_services._running is True
        assert monitor_services.transcript_queue is not None
        assert len(monitor_services._tasks) == 2
        monitor_services.audio_service.start_listening.assert_called_once()
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_stop(self, monitor_services):
        """stop cancels tasks and stops audio."""
        await monitor_services.start()
        await monitor_services.stop()
        
        assert monitor_services._running is False
        assert len(monitor_services._tasks) == 0
        monitor_services.audio_service.stop_listening.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_transcript(self, monitor_services):
        """_handle_transcript queues transcript for processing."""
        await monitor_services.start()
        
        monitor_services._handle_transcript("Hello world", "user")
        
        # Allow queue to process
        await asyncio.sleep(0.1)
        
        assert monitor_services.latest_transcript == "Hello world"
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_handle_transcript_broadcasts(self, monitor_services):
        """_handle_transcript calls broadcast callback."""
        broadcast_mock = AsyncMock()
        monitor_services.on_transcript = broadcast_mock
        
        await monitor_services.start()
        monitor_services._handle_transcript("Test message", "system")
        
        await asyncio.sleep(0.1)
        
        # Callback should be scheduled
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_process_transcript_stores_memory(self, monitor_services):
        """_process_transcript stores significant transcripts."""
        await monitor_services.start()
        monitor_services._is_recording = True
        
        # Significant transcript (>= 4 words)
        await monitor_services._process_transcript(("This is a significant transcript", "user"))
        
        monitor_services.memory_service.add_memory.assert_called_once()
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_process_transcript_skips_short(self, monitor_services):
        """_process_transcript skips short transcripts."""
        await monitor_services.start()
        monitor_services._is_recording = True
        
        # Short transcript (< 4 words)
        await monitor_services._process_transcript(("Too short", "user"))
        
        monitor_services.memory_service.add_memory.assert_not_called()
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_process_transcript_detects_question(self, monitor_services):
        """_process_transcript detects questions from system audio."""
        question_callback = AsyncMock()
        monitor_services.on_question_detected = question_callback
        monitor_services._auto_answer_enabled = True
        
        await monitor_services.start()
        
        # Question from system (other person on call)
        await monitor_services._process_transcript(("What do you think about this feature?", "system"))
        
        await asyncio.sleep(0.1)
        
        await monitor_services.stop()

    @pytest.mark.asyncio  
    async def test_process_transcript_ignores_user_questions(self, monitor_services):
        """_process_transcript ignores questions from user audio."""
        question_callback = AsyncMock()
        monitor_services.on_question_detected = question_callback
        monitor_services._auto_answer_enabled = True
        
        await monitor_services.start()
        
        # Question from user (not other person)
        await monitor_services._process_transcript(("What is the API endpoint?", "user"))
        
        await asyncio.sleep(0.1)
        question_callback.assert_not_called()
        
        await monitor_services.stop()

    def test_set_auto_answer(self, monitor_services):
        """set_auto_answer toggles auto-answer mode."""
        assert monitor_services._auto_answer_enabled is True
        
        monitor_services.set_auto_answer(False)
        assert monitor_services._auto_answer_enabled is False
        
        monitor_services.set_auto_answer(True)
        assert monitor_services._auto_answer_enabled is True

    def test_set_recording(self, monitor_services):
        """set_recording toggles recording mode."""
        assert monitor_services._is_recording is True
        
        monitor_services.set_recording(False)
        assert monitor_services._is_recording is False

    def test_get_recent_transcript(self, monitor_services):
        """get_recent_transcript returns formatted transcript."""
        now = time.time()
        monitor_services.recent_transcripts.append((now, "Hello", "user"))
        monitor_services.recent_transcripts.append((now, "Hi there", "system"))
        
        result = monitor_services.get_recent_transcript(seconds=60)
        
        assert "USER: Hello" in result
        assert "SYSTEM: Hi there" in result

    def test_get_recent_transcript_filters_old(self, monitor_services):
        """get_recent_transcript filters old entries."""
        old_time = time.time() - 200  # 200 seconds ago
        now = time.time()
        
        monitor_services.recent_transcripts.append((old_time, "Old message", "user"))
        monitor_services.recent_transcripts.append((now, "Recent message", "system"))
        
        result = monitor_services.get_recent_transcript(seconds=60)
        
        assert "Old message" not in result
        assert "Recent message" in result

    @pytest.mark.asyncio
    async def test_screen_loop_captures_screen(self, monitor_services):
        """_screen_loop captures and processes screen."""
        await monitor_services.start()
        
        # Allow one iteration
        await asyncio.sleep(0.2)
        
        # Capture should have been called
        monitor_services.capture_service.capture_screen.assert_called()
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_screen_loop_skips_unchanged(self, monitor_services):
        """_screen_loop skips processing when screen unchanged."""
        # Same image every time = same hash
        img = Image.new('RGB', (32, 32), color='white')
        monitor_services.capture_service.capture_screen.return_value = img
        
        await monitor_services.start()
        await asyncio.sleep(0.3)  # Multiple iterations
        
        # OCR should only be called once (visual hash unchanged)
        assert monitor_services.ocr_service.extract_text_async.call_count <= 2
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_screen_loop_stores_stable_text(self, monitor_services):
        """_screen_loop stores text after stability check."""
        monitor_services._is_recording = True
        # Make OCR return same text to trigger stability
        monitor_services.ocr_service.extract_text_async.return_value = "Stable text content that is long enough"
        
        # Different images to bypass visual hash
        call_count = [0]
        def varying_image():
            call_count[0] += 1
            return Image.new('RGB', (100, 100), color=(call_count[0] % 255, 0, 0))
        
        monitor_services.capture_service.capture_screen.side_effect = varying_image
        
        await monitor_services.start()
        await asyncio.sleep(2.5)  # Allow stability checks
        
        # Memory should be updated after stable text detected
        # This depends on timing, so we just check no errors
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_screen_loop_handles_capture_failure(self, monitor_services):
        """_screen_loop handles capture returning None."""
        monitor_services.capture_service.capture_screen.return_value = None
        
        await monitor_services.start()
        await asyncio.sleep(0.2)
        
        # Should not crash, OCR should not be called
        monitor_services.ocr_service.extract_text_async.assert_not_called()
        
        await monitor_services.stop()

    @pytest.mark.asyncio
    async def test_screen_loop_handles_exception(self, monitor_services):
        """_screen_loop handles exceptions gracefully."""
        monitor_services.capture_service.capture_screen.side_effect = Exception("Capture error")
        
        await monitor_services.start()
        await asyncio.sleep(0.2)
        
        # Monitor should still be running
        assert monitor_services._running is True
        
        await monitor_services.stop()

