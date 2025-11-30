"""
Integration tests for multimodal context flow.
Tests that audio and visual inputs are captured and processed together.
"""
import pytest
import asyncio
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock
from PIL import Image


@pytest.fixture
def multimodal_services():
    """Create mocked services for integration testing."""
    from app.services.capture import CaptureService
    from app.services.ocr import OCRService
    from app.services.memory import MemoryService
    
    capture = MagicMock(spec=CaptureService)
    img = Image.new('RGB', (100, 100), color='white')
    capture.capture_screen.return_value = img

    ocr = AsyncMock(spec=OCRService)
    ocr.extract_text_async.return_value = "Visual Context: User is looking at code."

    with patch('app.services.audio.sd') as mock_sd, \
         patch('app.services.audio.WhisperModel') as MockWhisper, \
         patch('torch.hub.load') as mock_hub:
        
        Segment = MagicMock()
        Segment.text = "Audio Context: Hello Computer."
        MockWhisper.return_value.transcribe.return_value = ([Segment], None)
        
        mock_vad = MagicMock()
        mock_vad.return_value.item.return_value = 0.8 
        mock_hub.return_value = (mock_vad, None)
        
        mock_sd.query_devices.return_value = [{'name': 'Mic', 'max_input_channels': 1}]
        mock_sd.default.device = [0, 0]

        from app.services.audio import AudioService
        audio = AudioService()
    
        memory = MagicMock(spec=MemoryService)

        yield {
            'capture': capture,
            'ocr': ocr,
            'audio': audio,
            'memory': memory,
        }


@pytest.mark.asyncio
async def test_multimodal_context_flow(multimodal_services):
    """Tests audio and visual inputs captured and combined."""
    from app.services.monitor import BackgroundMonitor
    
    monitor = BackgroundMonitor(
        capture_service=multimodal_services['capture'],
        ocr_service=multimodal_services['ocr'],
        audio_service=multimodal_services['audio'],
        memory_service=multimodal_services['memory'],
    )

    await monitor.start()
    
    # Simulate audio via transcript handling (bypasses hardware)
    monitor._handle_transcript("Audio Context: Hello Computer.", "user")
    
    # Allow processing
    await asyncio.sleep(0.3)
    
    # Verify OCR was called
    multimodal_services['ocr'].extract_text_async.assert_called()
    
    # Verify transcript processed
    assert monitor.latest_transcript == "Audio Context: Hello Computer."
    
    # Verify screen text captured
    assert monitor.latest_text == "Visual Context: User is looking at code."
    
    # Verify memory updated with transcript
    multimodal_services['memory'].add_memory.assert_called()
    
    # Verify recent transcripts tracked
    assert len(monitor.recent_transcripts) > 0
    
    # Get recent transcript should include audio context
    recent = monitor.get_recent_transcript(seconds=60)
    assert "Hello Computer" in recent
    
    await monitor.stop()


@pytest.mark.asyncio
async def test_audio_processing_pipeline(multimodal_services):
    """Tests audio transcription via device listener."""
    audio_service = multimodal_services['audio']
    
    # Start with a mock callback
    transcripts = []
    audio_service.start_listening(lambda text, src: transcripts.append((text, src)))
    
    if audio_service.listeners:
        listener = audio_service.listeners[0]
        
        # Feed speech chunks
        for _ in range(20):
            listener._process(np.random.rand(512).astype(np.float32))
        
        # Switch to silence to trigger transcription
        listener.vad_model.return_value.item.return_value = 0.0
        for _ in range(listener.max_silence_chunks + 2):
            listener._process(np.zeros(512).astype(np.float32))
        
        # Transcription should have occurred
        assert audio_service.model.transcribe.called


@pytest.mark.asyncio  
async def test_screen_capture_flow(multimodal_services):
    """Tests screen capture and OCR processing."""
    from app.services.monitor import BackgroundMonitor
    
    monitor = BackgroundMonitor(
        capture_service=multimodal_services['capture'],
        ocr_service=multimodal_services['ocr'],
        audio_service=multimodal_services['audio'],
        memory_service=multimodal_services['memory'],
    )
    
    await monitor.start()
    await asyncio.sleep(0.3)
    
    # Capture should have been called
    multimodal_services['capture'].capture_screen.assert_called()
    
    # OCR should have processed
    multimodal_services['ocr'].extract_text_async.assert_called()
    
    # Latest image should be set
    assert monitor.latest_image is not None
    
    await monitor.stop()


@pytest.mark.asyncio
async def test_question_detection_from_system_audio(multimodal_services):
    """Tests question detection triggers callback."""
    from app.services.monitor import BackgroundMonitor
    
    monitor = BackgroundMonitor(
        capture_service=multimodal_services['capture'],
        ocr_service=multimodal_services['ocr'],
        audio_service=multimodal_services['audio'],
        memory_service=multimodal_services['memory'],
    )
    
    question_detected = []
    
    async def on_question(q):
        question_detected.append(q)
    
    monitor.on_question_detected = on_question
    monitor._auto_answer_enabled = True
    
    await monitor.start()
    
    # System audio with question should trigger detection
    monitor._handle_transcript("What do you think about this approach?", "system")
    
    await asyncio.sleep(0.2)
    
    # Question should be detected
    assert len(question_detected) == 1
    assert "approach" in question_detected[0]
    
    await monitor.stop()


@pytest.mark.asyncio
async def test_user_questions_not_auto_answered(multimodal_services):
    """Tests user questions don't trigger auto-answer."""
    from app.services.monitor import BackgroundMonitor
    
    monitor = BackgroundMonitor(
        capture_service=multimodal_services['capture'],
        ocr_service=multimodal_services['ocr'],
        audio_service=multimodal_services['audio'],
        memory_service=multimodal_services['memory'],
    )
    
    question_detected = []
    monitor.on_question_detected = AsyncMock(side_effect=question_detected.append)
    monitor._auto_answer_enabled = True
    
    await monitor.start()
    
    # User audio question should NOT trigger
    monitor._handle_transcript("What is the best way to do this?", "user")
    
    await asyncio.sleep(0.2)
    
    assert len(question_detected) == 0
    
    await monitor.stop()
