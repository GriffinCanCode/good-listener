"""Shared test fixtures for the Good Listener backend test suite."""
import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def dummy_image() -> Image.Image:
    """Create a test image."""
    return Image.new('RGB', (100, 100), color='white')


@pytest.fixture
def dummy_audio() -> np.ndarray:
    """Create test audio data (1 second at 16kHz)."""
    return np.random.rand(16000).astype(np.float32)


@pytest.fixture
def mock_mss():
    """Mock screen capture library."""
    with patch('mss.mss') as mock:
        mock_instance = MagicMock()
        mock_instance.monitors = [
            {'width': 1920, 'height': 1080},  # All monitors combined
            {'left': 0, 'top': 0, 'width': 1920, 'height': 1080},  # Primary
        ]
        mock_sct = MagicMock()
        mock_sct.size = (1920, 1080)
        mock_sct.bgra = b'\x00' * (1920 * 1080 * 4)
        mock_instance.grab.return_value = mock_sct
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice library."""
    with patch('app.services.audio.sd') as mock_sd:
        mock_sd.query_devices.return_value = [
            {'name': 'Default Microphone', 'max_input_channels': 1, 'default_samplerate': 16000},
            {'name': 'BlackHole 2ch', 'max_input_channels': 2, 'default_samplerate': 16000},
        ]
        mock_sd.default.device = [0, 0]
        mock_sd.InputStream = MagicMock()
        yield mock_sd


@pytest.fixture
def mock_whisper():
    """Mock Whisper model."""
    with patch('app.services.audio.WhisperModel') as MockWhisper:
        mock_model = MagicMock()
        segment = MagicMock()
        segment.text = "Test transcription."
        mock_model.transcribe.return_value = ([segment], None)
        MockWhisper.return_value = mock_model
        yield mock_model


@pytest.fixture
def mock_vad():
    """Mock Silero VAD model."""
    with patch('torch.hub.load') as mock_hub:
        mock_vad_model = MagicMock()
        mock_vad_model.return_value.item.return_value = 0.8  # Simulate speech
        mock_hub.return_value = (mock_vad_model, None)
        yield mock_vad_model


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    with patch('app.services.memory.chromadb.PersistentClient') as MockClient:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 100
        mock_collection.query.return_value = {
            'documents': [['Previous context about coding.']],
            'ids': [['audio_123']],
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        MockClient.return_value = mock_client
        yield mock_collection


@pytest.fixture
def mock_rapidocr():
    """Mock RapidOCR engine."""
    with patch('app.services.ocr.RapidOCR') as MockOCR:
        mock_engine = MagicMock()
        # Return OCR results with bounding boxes: [[box, text, confidence], ...]
        mock_engine.return_value = (
            [
                [[[0, 0], [100, 0], [100, 20], [0, 20]], "Hello World", 0.95],
                [[[0, 30], [150, 30], [150, 50], [0, 50]], "Test Text", 0.92],
            ],
            None
        )
        MockOCR.return_value = mock_engine
        yield mock_engine


@pytest.fixture
def mock_llm():
    """Mock LLM service."""
    async def async_gen():
        for chunk in ["Test ", "response ", "from ", "LLM."]:
            yield chunk

    mock = AsyncMock()
    mock.analyze = MagicMock(side_effect=lambda *a, **k: async_gen())
    return mock


@pytest.fixture
def mock_capture_service():
    """Mock CaptureService."""
    mock = MagicMock()
    mock.capture_screen.return_value = Image.new('RGB', (100, 100), color='white')
    return mock


@pytest.fixture
def mock_ocr_service():
    """Mock OCRService."""
    mock = AsyncMock()
    mock.extract_text_async.return_value = "[0, 0, 100, 20] Test screen text"
    mock.extract_text.return_value = "[0, 0, 100, 20] Test screen text"
    return mock


@pytest.fixture
def mock_audio_service():
    """Mock AudioService."""
    mock = MagicMock()
    mock.listeners = []
    mock.start_listening = MagicMock()
    mock.stop_listening = MagicMock()
    return mock


@pytest.fixture
def mock_memory_service():
    """Mock MemoryService."""
    mock = MagicMock()
    mock.add_memory = MagicMock()
    mock.query_memory.return_value = ["Previous context."]
    return mock


@pytest.fixture
def mock_all_services(mock_capture_service, mock_ocr_service, mock_audio_service, mock_memory_service, mock_llm):
    """Bundle of all mocked services."""
    return {
        'capture': mock_capture_service,
        'ocr': mock_ocr_service,
        'audio': mock_audio_service,
        'memory': mock_memory_service,
        'llm': mock_llm,
    }


@pytest.fixture
def mock_monitor(mock_all_services):
    """Mock BackgroundMonitor."""
    mock = MagicMock()
    mock.latest_text = "Test screen text"
    mock.latest_transcript = "Test transcript"
    mock.latest_image = Image.new('RGB', (100, 100))
    mock.get_recent_transcript.return_value = "USER: Hello\nSYSTEM: Hi there"
    mock.set_recording = MagicMock()
    mock.set_auto_answer = MagicMock()
    return mock


@pytest.fixture
def test_app(mock_monitor) -> Generator[FastAPI, None, None]:
    """Create test FastAPI app with mocked monitor."""
    from app.main import app
    app.state.monitor = mock_monitor
    yield app


@pytest.fixture
def client(test_app) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(test_app) as c:
        yield c

