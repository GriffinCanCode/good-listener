"""Tests for centralized configuration."""

import json
import os
from pathlib import Path

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
    get_schema,
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


# ========== Schema Drift Detection Tests ==========

class TestSchemaDrift:
    """Tests ensuring Python config stays synchronized with schema.json."""

    @pytest.fixture
    def schema(self) -> dict:
        return get_schema()

    def test_inference_fields_match_schema(self, schema: dict):
        """Verify InferenceConfig fields match schema.inference properties."""
        schema_props = schema["properties"]["inference"]["properties"]
        config_fields = {f.name for f in InferenceConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_audio_fields_match_schema(self, schema: dict):
        """Verify AudioConfig fields match schema.audio properties."""
        schema_props = schema["properties"]["audio"]["properties"]
        config_fields = {f.name for f in AudioConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_screen_fields_match_schema(self, schema: dict):
        """Verify ScreenConfig fields match schema.screen properties."""
        schema_props = schema["properties"]["screen"]["properties"]
        config_fields = {f.name for f in ScreenConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_llm_fields_match_schema(self, schema: dict):
        """Verify LLMConfig fields match schema.llm properties."""
        schema_props = schema["properties"]["llm"]["properties"]
        config_fields = {f.name for f in LLMConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_memory_fields_match_schema(self, schema: dict):
        """Verify MemoryConfig fields match schema.memory properties."""
        schema_props = schema["properties"]["memory"]["properties"]
        config_fields = {f.name for f in MemoryConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_auto_answer_fields_match_schema(self, schema: dict):
        """Verify AutoAnswerConfig fields match schema.auto_answer properties."""
        schema_props = schema["properties"]["auto_answer"]["properties"]
        config_fields = {f.name for f in AutoAnswerConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_logging_fields_match_schema(self, schema: dict):
        """Verify LoggingConfig fields match schema.logging properties."""
        schema_props = schema["properties"]["logging"]["properties"]
        config_fields = {f.name for f in LoggingConfig.__dataclass_fields__.values()}
        schema_fields = set(schema_props.keys())
        assert config_fields == schema_fields, f"Drift: config={config_fields}, schema={schema_fields}"

    def test_defaults_match_schema(self, schema: dict):
        """Verify default values match schema defaults."""
        cfg = Config()  # Uses all defaults
        mismatches = []

        checks = [
            ("inference.grpc_port", cfg.inference.grpc_port, schema["properties"]["inference"]["properties"]["grpc_port"]["default"]),
            ("inference.grpc_max_workers", cfg.inference.grpc_max_workers, schema["properties"]["inference"]["properties"]["grpc_max_workers"]["default"]),
            ("audio.sample_rate", cfg.audio.sample_rate, schema["properties"]["audio"]["properties"]["sample_rate"]["default"]),
            ("audio.vad_threshold", cfg.audio.vad_threshold, schema["properties"]["audio"]["properties"]["vad_threshold"]["default"]),
            ("audio.max_silence_chunks", cfg.audio.max_silence_chunks, schema["properties"]["audio"]["properties"]["max_silence_chunks"]["default"]),
            ("screen.capture_rate", cfg.screen.capture_rate, schema["properties"]["screen"]["properties"]["capture_rate"]["default"]),
            ("screen.stable_count_threshold", cfg.screen.stable_count_threshold, schema["properties"]["screen"]["properties"]["stable_count_threshold"]["default"]),
            ("llm.provider", cfg.llm.provider, schema["properties"]["llm"]["properties"]["provider"]["default"]),
            ("llm.model", cfg.llm.model, schema["properties"]["llm"]["properties"]["model"]["default"]),
            ("memory.query_default_results", cfg.memory.query_default_results, schema["properties"]["memory"]["properties"]["query_default_results"]["default"]),
            ("memory.batch_max_size", cfg.memory.batch_max_size, schema["properties"]["memory"]["properties"]["batch_max_size"]["default"]),
            ("auto_answer.enabled", cfg.auto_answer.enabled, schema["properties"]["auto_answer"]["properties"]["enabled"]["default"]),
            ("auto_answer.cooldown_seconds", cfg.auto_answer.cooldown_seconds, schema["properties"]["auto_answer"]["properties"]["cooldown_seconds"]["default"]),
            ("logging.level", cfg.logging.level, schema["properties"]["logging"]["properties"]["level"]["default"]),
            ("logging.format", cfg.logging.format, schema["properties"]["logging"]["properties"]["format"]["default"]),
        ]

        for path, actual, expected in checks:
            if actual != expected:
                mismatches.append(f"{path}: got {actual!r}, schema has {expected!r}")

        assert not mismatches, f"Default value drift:\n  - " + "\n  - ".join(mismatches)

