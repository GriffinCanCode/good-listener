"""Tests for centralized configuration."""

import os

import pytest

from app.core.config import (
    AudioConfig,
    AutoAnswerConfig,
    Config,
    InferenceConfig,
    LLMConfig,
    LoggingConfig,
    MemoryConfig,
    ScreenConfig,
    load_config,
)


@pytest.fixture(autouse=True)
def clean_env():
    """Clear config-related env vars before each test."""
    env_vars = [
        "GRPC_PORT", "GRPC_MAX_WORKERS", "GRPC_SHUTDOWN_GRACE_PERIOD",
        "SAMPLE_RATE", "VAD_THRESHOLD", "MAX_SILENCE_CHUNKS", "CAPTURE_SYSTEM_AUDIO",
        "EXCLUDED_AUDIO_DEVICES", "SCREEN_CAPTURE_RATE", "SCREEN_STABLE_COUNT_THRESHOLD",
        "SCREEN_MIN_TEXT_LENGTH", "SCREEN_PHASH_THRESHOLD", "LLM_PROVIDER", "LLM_MODEL",
        "OLLAMA_HOST", "LLM_CONTEXT_MAX_LENGTH", "LLM_SCREEN_CONTEXT_MAX_LENGTH",
        "MEMORY_QUERY_RESULTS", "MEMORY_PRUNE_THRESHOLD", "MEMORY_PRUNE_KEEP",
        "MEMORY_BATCH_MAX_SIZE", "MEMORY_BATCH_FLUSH_DELAY_MS", "AUTO_ANSWER_ENABLED",
        "AUTO_ANSWER_COOLDOWN", "MIN_QUESTION_LENGTH", "LOG_LEVEL", "LOG_FORMAT",
    ]
    for var in env_vars:
        os.environ.pop(var, None)
    # Reset singleton
    import app.core.config as cfg_module
    cfg_module._config = None
    yield
    for var in env_vars:
        os.environ.pop(var, None)
    cfg_module._config = None


def test_load_defaults():
    """Test that defaults are loaded correctly."""
    cfg = load_config()
    
    assert cfg.inference.grpc_port == 50051
    assert cfg.inference.grpc_max_workers == 10
    assert cfg.audio.sample_rate == 16000
    assert cfg.audio.vad_threshold == 0.5
    assert cfg.screen.capture_rate == 1.0
    assert cfg.llm.provider == "gemini"
    assert cfg.memory.query_default_results == 5
    assert cfg.auto_answer.enabled is True
    assert cfg.logging.level == "INFO"


def test_load_from_env():
    """Test that env vars override defaults."""
    os.environ["GRPC_PORT"] = "50052"
    os.environ["SAMPLE_RATE"] = "48000"
    os.environ["VAD_THRESHOLD"] = "0.7"
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["AUTO_ANSWER_ENABLED"] = "false"
    os.environ["LOG_LEVEL"] = "debug"
    
    cfg = load_config()
    
    assert cfg.inference.grpc_port == 50052
    assert cfg.audio.sample_rate == 48000
    assert cfg.audio.vad_threshold == 0.7
    assert cfg.llm.provider == "ollama"
    assert cfg.auto_answer.enabled is False
    assert cfg.logging.level == "DEBUG"


def test_validation_invalid_sample_rate():
    """Test that invalid sample rate fails validation."""
    os.environ["SAMPLE_RATE"] = "12345"
    
    with pytest.raises(ValueError, match="sample_rate"):
        load_config()


def test_validation_vad_threshold_out_of_range():
    """Test that VAD threshold > 1 fails validation."""
    os.environ["VAD_THRESHOLD"] = "1.5"
    
    with pytest.raises(ValueError, match="vad_threshold"):
        load_config()


def test_validation_screen_capture_rate_too_low():
    """Test that capture rate < 0.1 fails validation."""
    os.environ["SCREEN_CAPTURE_RATE"] = "0.05"
    
    with pytest.raises(ValueError, match="capture_rate"):
        load_config()


def test_validation_prune_keep_exceeds_threshold():
    """Test that prune_keep >= prune_threshold fails validation."""
    os.environ["MEMORY_PRUNE_KEEP"] = "15000"
    os.environ["MEMORY_PRUNE_THRESHOLD"] = "10000"
    
    with pytest.raises(ValueError, match="prune_keep"):
        load_config()


def test_config_immutable():
    """Test that config dataclasses are frozen."""
    cfg = load_config()
    
    with pytest.raises(AttributeError):
        cfg.inference.grpc_port = 9999  # type: ignore[misc]


def test_excluded_devices_parsing():
    """Test comma-separated device list parsing."""
    os.environ["EXCLUDED_AUDIO_DEVICES"] = "iphone, airpods, teams"
    
    cfg = load_config()
    
    assert cfg.audio.excluded_devices == ("iphone", "airpods", "teams")

