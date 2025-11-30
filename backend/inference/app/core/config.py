"""Centralized configuration with JSON schema validation.

Loads config from environment variables and validates against shared schema.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Schema path relative to this file (backend/inference/app/core/config.py -> backend/config/schema.json)
SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "config" / "schema.json"


@dataclass(frozen=True, slots=True)
class InferenceConfig:
    """Inference service gRPC configuration."""

    grpc_port: int = 50051
    grpc_max_workers: int = 10
    grpc_shutdown_grace_period: float = 10.0


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Audio processing configuration."""

    sample_rate: int = 16000
    vad_threshold: float = 0.5
    max_silence_chunks: int = 15
    capture_system_audio: bool = True
    excluded_devices: tuple[str, ...] = ("iphone", "teams")


@dataclass(frozen=True, slots=True)
class ScreenConfig:
    """Screen capture configuration."""

    capture_rate: float = 1.0
    stable_count_threshold: int = 2
    min_text_length: int = 10
    phash_similarity_threshold: float = 0.95


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """LLM service configuration."""

    provider: Literal["gemini", "ollama"] = "gemini"
    model: str = "gemini-2.0-flash"
    ollama_host: str = "http://localhost:11434"
    context_max_length: int = 5000
    screen_context_max_length: int = 2000


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Vector memory configuration."""

    query_default_results: int = 5
    prune_threshold: int = 10000
    prune_keep: int = 5000
    batch_max_size: int = 50
    batch_flush_delay_ms: int = 2000


@dataclass(frozen=True, slots=True)
class AutoAnswerConfig:
    """Auto-answer feature configuration."""

    enabled: bool = True
    cooldown_seconds: float = 10.0
    min_question_length: int = 10


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["json", "text"] = "text"


@dataclass(slots=True)
class Config:
    """Root configuration container with validation."""

    inference: InferenceConfig = field(default_factory=InferenceConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    auto_answer: AutoAnswerConfig = field(default_factory=AutoAnswerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def validate(self) -> list[str]:
        """Validate config against schema constraints. Returns list of errors."""
        errors: list[str] = []
        # Audio validation
        if self.audio.sample_rate not in (8000, 16000, 22050, 44100, 48000):
            errors.append(f"audio.sample_rate must be one of [8000, 16000, 22050, 44100, 48000], got {self.audio.sample_rate}")
        if not 0 <= self.audio.vad_threshold <= 1:
            errors.append(f"audio.vad_threshold must be 0-1, got {self.audio.vad_threshold}")
        # Inference validation
        if not 1 <= self.inference.grpc_port <= 65535:
            errors.append(f"inference.grpc_port must be 1-65535, got {self.inference.grpc_port}")
        if not 1 <= self.inference.grpc_max_workers <= 100:
            errors.append(f"inference.grpc_max_workers must be 1-100, got {self.inference.grpc_max_workers}")
        # Screen validation
        if not 0.1 <= self.screen.capture_rate <= 10:
            errors.append(f"screen.capture_rate must be 0.1-10, got {self.screen.capture_rate}")
        if not 0 <= self.screen.phash_similarity_threshold <= 1:
            errors.append(f"screen.phash_similarity_threshold must be 0-1, got {self.screen.phash_similarity_threshold}")
        # LLM validation
        if self.llm.provider not in ("gemini", "ollama"):
            errors.append(f"llm.provider must be 'gemini' or 'ollama', got {self.llm.provider}")
        # Memory validation
        if self.memory.prune_keep >= self.memory.prune_threshold:
            errors.append(f"memory.prune_keep ({self.memory.prune_keep}) must be < prune_threshold ({self.memory.prune_threshold})")
        return errors


def _parse_bool(val: str) -> bool:
    return val.lower() in ("true", "1", "yes")


def _parse_list(val: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in val.split(",") if p.strip())


def load_config() -> Config:
    """Load configuration from environment variables with validation."""
    cfg = Config(
        inference=InferenceConfig(
            grpc_port=int(os.getenv("GRPC_PORT", "50051")),
            grpc_max_workers=int(os.getenv("GRPC_MAX_WORKERS", "10")),
            grpc_shutdown_grace_period=float(os.getenv("GRPC_SHUTDOWN_GRACE_PERIOD", "10")),
        ),
        audio=AudioConfig(
            sample_rate=int(os.getenv("SAMPLE_RATE", "16000")),
            vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
            max_silence_chunks=int(os.getenv("MAX_SILENCE_CHUNKS", "15")),
            capture_system_audio=_parse_bool(os.getenv("CAPTURE_SYSTEM_AUDIO", "true")),
            excluded_devices=_parse_list(os.getenv("EXCLUDED_AUDIO_DEVICES", "iphone,teams")),
        ),
        screen=ScreenConfig(
            capture_rate=float(os.getenv("SCREEN_CAPTURE_RATE", "1.0")),
            stable_count_threshold=int(os.getenv("SCREEN_STABLE_COUNT_THRESHOLD", "2")),
            min_text_length=int(os.getenv("SCREEN_MIN_TEXT_LENGTH", "10")),
            phash_similarity_threshold=float(os.getenv("SCREEN_PHASH_THRESHOLD", "0.95")),
        ),
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "gemini"),  # type: ignore[arg-type]
            model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            context_max_length=int(os.getenv("LLM_CONTEXT_MAX_LENGTH", "5000")),
            screen_context_max_length=int(os.getenv("LLM_SCREEN_CONTEXT_MAX_LENGTH", "2000")),
        ),
        memory=MemoryConfig(
            query_default_results=int(os.getenv("MEMORY_QUERY_RESULTS", "5")),
            prune_threshold=int(os.getenv("MEMORY_PRUNE_THRESHOLD", "10000")),
            prune_keep=int(os.getenv("MEMORY_PRUNE_KEEP", "5000")),
            batch_max_size=int(os.getenv("MEMORY_BATCH_MAX_SIZE", "50")),
            batch_flush_delay_ms=int(os.getenv("MEMORY_BATCH_FLUSH_DELAY_MS", "2000")),
        ),
        auto_answer=AutoAnswerConfig(
            enabled=_parse_bool(os.getenv("AUTO_ANSWER_ENABLED", "true")),
            cooldown_seconds=float(os.getenv("AUTO_ANSWER_COOLDOWN", "10")),
            min_question_length=int(os.getenv("MIN_QUESTION_LENGTH", "10")),
        ),
        logging=LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),  # type: ignore[arg-type]
            format=os.getenv("LOG_FORMAT", "text").lower(),  # type: ignore[arg-type]
        ),
    )
    if errors := cfg.validate():
        raise ValueError(f"Configuration validation failed:\n  - " + "\n  - ".join(errors))
    return cfg


def get_schema() -> dict:
    """Load and return the JSON schema."""
    return json.loads(SCHEMA_PATH.read_text())


# Singleton config instance - loaded once at import
_config: Config | None = None


def get_config() -> Config:
    """Get the singleton config instance, loading on first call."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

