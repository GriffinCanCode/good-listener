"""
Core module: logging, schemas, and shared infrastructure.
"""

from app.core.logging import (
    get_logger,
    set_correlation_id,
    get_correlation_id,
    configure_logging,
    StructuredLogger,
    Colors,
)
from app.core.schemas import (
    WebSocketPayload,
    TranscriptPayload,
    ChunkPayload,
    StartPayload,
    DonePayload,
    AutoAnswerPayload,
    AutoAnswerChunkPayload,
    AutoAnswerStartPayload,
    AutoAnswerDonePayload,
    ChatRequest,
    CaptureResponse,
    RecordingStatusResponse,
)

__all__ = [
    # Logging
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "configure_logging",
    "StructuredLogger",
    "Colors",
    # Schemas
    "WebSocketPayload",
    "TranscriptPayload",
    "ChunkPayload",
    "StartPayload",
    "DonePayload",
    "AutoAnswerPayload",
    "AutoAnswerChunkPayload",
    "AutoAnswerStartPayload",
    "AutoAnswerDonePayload",
    "ChatRequest",
    "CaptureResponse",
    "RecordingStatusResponse",
]

