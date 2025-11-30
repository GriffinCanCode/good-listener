import pytest
import asyncio
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock
from PIL import Image
from app.services.monitor import BackgroundMonitor
from app.services.audio import AudioService, DeviceListener
from app.services.capture import CaptureService
from app.services.ocr import OCRService
from app.services.llm import LLMService
from app.services.memory import MemoryService

@pytest.fixture
def mock_services():
    capture = MagicMock(spec=CaptureService)
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color='white')
    capture.capture_screen.return_value = img

    ocr = AsyncMock(spec=OCRService)
    ocr.extract_text_async.return_value = "Visual Context: User is looking at code."

    # Audio Service with mocks
    # We mock the hardware/model parts but keep the logic
    with patch('app.services.audio.sd') as mock_sd, \
         patch('app.services.audio.WhisperModel') as MockWhisper, \
         patch('torch.hub.load') as mock_hub:
        
        # Setup Whisper Mock
        mock_model_instance = MockWhisper.return_value
        # transcribe returns (segments, info)
        Segment = MagicMock()
        Segment.text = "Audio Context: Hello Computer."
        mock_model_instance.transcribe.return_value = ([Segment], None)
        
        # Setup VAD Mock
        mock_vad = MagicMock()
        # Return > 0.5 to trigger speech
        mock_vad.return_value.item.return_value = 0.8 
        mock_hub.return_value = (mock_vad, None)
        
        # Setup SoundDevice Mock
        mock_sd.query_devices.return_value = [{'name': 'Mic', 'max_input_channels': 1}]
        mock_sd.default.device = [0, 0]

        audio = AudioService()
    
        memory = MagicMock(spec=MemoryService)
        
        llm = AsyncMock(spec=LLMService)
        
        # Helper for async generator
        async def async_gen():
            yield "Insight: "
            yield "I see you are coding."

        # Analyze is called and returns an async iterator
        llm.analyze = MagicMock(side_effect=lambda *a, **k: async_gen())

        yield {
            'capture': capture,
            'ocr': ocr,
            'audio': audio,
            'memory': memory,
            'llm': llm
        }

@pytest.mark.asyncio
async def test_multimodal_context_flow(mock_services):
    """
    Tests that audio and visual inputs are captured, processed, 
    and combined into a prompt for the LLM.
    """
    monitor = BackgroundMonitor(
        capture_service=mock_services['capture'],
        ocr_service=mock_services['ocr'],
        audio_service=mock_services['audio'],
        memory_service=mock_services['memory'],
        llm_service=mock_services['llm']
    )

    # 1. Start Monitor
    await monitor.start()
    
    # 2. Simulate Audio Input
    # We manually trigger the processing logic in the listener
    # equivalent to hardware callback + internal loop
    listener = monitor.audio_service.listeners[0]
    
    # Feed enough chunks to trigger VAD and then silence to trigger transcribe
    # Chunk size 512. Sample rate 16000.
    # We need ~0.5s of speech (8000 samples) + silence
    
    # Speech
    speech_chunk = np.random.rand(512).astype(np.float32)
    for _ in range(20): # ~10k samples
        listener._process(speech_chunk)
        
    # Silence
    # We need to patch VAD to return 0 now
    listener.vad_model.return_value.item.return_value = 0.0
    
    silence_chunk = np.zeros(512).astype(np.float32)
    for _ in range(listener.max_silence_chunks + 2):
        listener._process(silence_chunk)
        
    # 3. Allow async loop to process
    await asyncio.sleep(1) 
    
    # 4. Verify Results
    
    # Check if OCR was called
    mock_services['ocr'].extract_text_async.assert_called()
    
    # Check if Memory was updated with both contexts
    # Audio memory
    mock_services['memory'].add_memory.assert_any_call("Audio Context: Hello Computer.", "audio")
    # Screen memory (might take a few loops in monitor, monitor sleeps 5s)
    # We can force the check or wait? monitor._screen_loop sleeps 5s.
    # We can't easily wait 5s in a fast test.
    # We'll inspect internal state
    assert monitor.latest_text == "Visual Context: User is looking at code."
    
    # Check if LLM was called with combined context
    # llm.analyze(latest_text, prompt, latest_image)
    assert mock_services['llm'].analyze.called
    call_args = mock_services['llm'].analyze.call_args
    _, prompt, _ = call_args[0]
    
    print(f"Generated Prompt: {prompt}")
    
    assert "Audio Context: Hello Computer." in prompt
    assert "Visual Context: User is looking at code." in prompt

    await monitor.stop()

