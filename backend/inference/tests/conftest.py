"""Test fixtures for inference services."""

import pytest
from unittest.mock import MagicMock
import numpy as np
from PIL import Image


@pytest.fixture
def sample_audio():
    """Generate sample audio data (1 second of silence at 16kHz)."""
    return np.zeros(16000, dtype=np.float32)


@pytest.fixture
def sample_image():
    """Generate a sample test image."""
    return Image.new("RGB", (100, 100), color="white")


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.0-flash")


@pytest.fixture
def mock_rapidocr():
    """Mock RapidOCR engine."""
    mock = MagicMock()
    # Return sample OCR results: list of (bbox, text, confidence)
    mock.return_value = (
        [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Hello World", 0.95),
            ([[0, 30], [150, 30], [150, 50], [0, 50]], "Test Text", 0.88),
        ],
        None,
    )
    return mock


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB collection."""
    mock = MagicMock()
    mock.add = MagicMock()
    mock.query = MagicMock(return_value={
        "ids": [["id_1", "id_2"]],
        "documents": [["Relevant memory 1", "Relevant memory 2"]],
        "metadatas": [[{"source": "audio", "access_count": 0}, {"source": "screen", "access_count": 0}]],
        "distances": [[0.1, 0.2]],
    })
    mock.count = MagicMock(return_value=100)
    mock.get = MagicMock(return_value={"ids": [], "metadatas": []})
    mock.delete = MagicMock()
    mock.update = MagicMock()
    return mock


@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model."""
    mock = MagicMock()
    segment = MagicMock()
    segment.text = "Hello, this is a test."
    mock.transcribe = MagicMock(return_value=([segment], MagicMock(language_probability=0.98)))
    return mock


@pytest.fixture
def mock_vad_model():
    """Mock Silero VAD model."""
    mock = MagicMock()
    mock.return_value = MagicMock(item=MagicMock(return_value=0.8))
    mock.reset_states = MagicMock()
    return mock


@pytest.fixture
def mock_llm():
    """Mock LLM for streaming responses."""
    mock = MagicMock()
    
    async def mock_astream(messages):
        chunks = ["Hello", ", ", "world", "!"]
        for chunk in chunks:
            yield MagicMock(content=chunk)
    
    mock.astream = mock_astream
    return mock
