"""
Good Listener - AI-powered screen and audio assistant.
"""

__version__ = "0.1.0"
__app_name__ = "good-listener"

from app.core import (
    get_logger, set_correlation_id, configure_logging,
    WebSocketPayload, TranscriptPayload, ChunkPayload, StartPayload, DonePayload,
    AutoAnswerPayload, AutoAnswerChunkPayload, AutoAnswerStartPayload, AutoAnswerDonePayload,
    ChatRequest, CaptureResponse, RecordingStatusResponse,
)

__all__ = [
    "__version__",
    "__app_name__",
    # Logging
    "get_logger",
    "set_correlation_id", 
    "configure_logging",
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

