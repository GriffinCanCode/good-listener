"""Error handling with codes compatible across Python, Go, and TypeScript.

Uses protobuf-defined ErrorCode enum for cross-language consistency.
Error codes are defined in cognition.proto and shared across all services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import app.pb.cognition_pb2 as pb

if TYPE_CHECKING:
    import grpc

# Re-export protobuf ErrorCode for convenience (int-based enum)
ErrorCode = pb.ErrorCode

# Map protobuf ErrorCode to gRPC StatusCode (int values)
_GRPC_CODE_MAP: dict[int, int] = {
    pb.ERROR_CODE_UNSPECIFIED: 2,  # UNKNOWN
    pb.UNKNOWN: 2,  # UNKNOWN
    pb.INTERNAL: 13,  # INTERNAL
    pb.INVALID_ARGUMENT: 3,  # INVALID_ARGUMENT
    pb.NOT_FOUND: 5,  # NOT_FOUND
    pb.UNAVAILABLE: 14,  # UNAVAILABLE
    pb.TIMEOUT: 4,  # DEADLINE_EXCEEDED
    pb.CANCELLED: 1,  # CANCELLED
    # Audio domain
    pb.AUDIO_INVALID_FORMAT: 3,
    pb.AUDIO_EMPTY_INPUT: 3,
    pb.AUDIO_TRANSCRIPTION_FAILED: 13,
    pb.AUDIO_VAD_FAILED: 13,
    pb.AUDIO_DIARIZATION_FAILED: 13,
    pb.AUDIO_MODEL_LOAD_FAILED: 14,
    # LLM domain
    pb.LLM_NOT_CONFIGURED: 9,  # FAILED_PRECONDITION
    pb.LLM_API_ERROR: 13,
    pb.LLM_RATE_LIMITED: 8,  # RESOURCE_EXHAUSTED
    pb.LLM_CONTEXT_TOO_LONG: 3,
    pb.LLM_INVALID_RESPONSE: 13,
    # Memory domain
    pb.MEMORY_STORE_FAILED: 13,
    pb.MEMORY_QUERY_FAILED: 13,
    pb.MEMORY_POOL_EXHAUSTED: 8,
    pb.MEMORY_INIT_FAILED: 14,
    # OCR domain
    pb.OCR_INIT_FAILED: 14,
    pb.OCR_EXTRACT_FAILED: 13,
    pb.OCR_INVALID_IMAGE: 3,
    # Config domain
    pb.CONFIG_INVALID: 3,
    pb.CONFIG_MISSING: 9,
}


def error_code_name(code: int) -> str:
    """Get the string name of an error code."""
    return pb.ErrorCode.Name(code) if code in pb.ErrorCode.values() else "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ErrorDetails:
    """Structured error information for cross-service communication."""

    code: int
    message: str
    metadata: dict[str, str] | None = None

    def to_dict(self) -> dict:
        return {"code": error_code_name(self.code), "message": self.message, **({"metadata": self.metadata} if self.metadata else {})}

    def to_proto(self) -> pb.ErrorDetail:
        """Convert to protobuf ErrorDetail message."""
        detail = pb.ErrorDetail(code=self.code, message=self.message)
        if self.metadata:
            detail.metadata.update(self.metadata)
        return detail


class AppError(Exception):
    """Base exception for all application errors."""

    code: int = pb.INTERNAL

    def __init__(self, message: str, *, code: int | None = None, cause: Exception | None = None, **metadata: str):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.message = message
        self.cause = cause
        self.metadata = metadata or None

    @property
    def grpc_code(self) -> int:
        return _GRPC_CODE_MAP.get(self.code, 2)

    @property
    def code_name(self) -> str:
        return error_code_name(self.code)

    def to_error_details(self) -> ErrorDetails:
        return ErrorDetails(code=self.code, message=self.message, metadata=self.metadata)

    def to_proto(self) -> pb.ErrorDetail:
        """Convert to protobuf ErrorDetail for gRPC status details."""
        return self.to_error_details().to_proto()

    def __str__(self) -> str:
        parts = [f"[{self.code_name}] {self.message}"]
        if self.metadata:
            parts.append(f" ({', '.join(f'{k}={v}' for k, v in self.metadata.items())})")
        if self.cause:
            parts.append(f" caused by: {self.cause}")
        return "".join(parts)


# Domain-specific exceptions

class AudioError(AppError):
    """Audio processing errors."""
    code = pb.AUDIO_TRANSCRIPTION_FAILED


class TranscriptionError(AudioError):
    """Transcription-specific errors."""
    code = pb.AUDIO_TRANSCRIPTION_FAILED


class VADError(AudioError):
    """Voice activity detection errors."""
    code = pb.AUDIO_VAD_FAILED


class DiarizationError(AudioError):
    """Speaker diarization errors."""
    code = pb.AUDIO_DIARIZATION_FAILED


class LLMError(AppError):
    """Language model errors."""
    code = pb.LLM_API_ERROR


class MemoryError(AppError):
    """Vector memory/store errors."""
    code = pb.MEMORY_STORE_FAILED


class OCRError(AppError):
    """OCR/screen text extraction errors."""
    code = pb.OCR_EXTRACT_FAILED


class ConfigError(AppError):
    """Configuration errors."""
    code = pb.CONFIG_INVALID


# gRPC integration utilities

def abort_with_error(context: grpc.ServicerContext, err: AppError) -> None:
    """Abort gRPC call with structured error and status details."""
    import grpc as grpc_module
    from grpc_status import rpc_status
    from google.rpc import status_pb2
    from google.protobuf import any_pb2

    # Create status with error detail
    detail = any_pb2.Any()
    detail.Pack(err.to_proto())

    status = status_pb2.Status(
        code=err.grpc_code,
        message=str(err),
        details=[detail],
    )

    # Abort with rich status
    context.abort_with_status(rpc_status.to_status(status))


def abort_with_error_simple(context: grpc.ServicerContext, err: AppError) -> None:
    """Abort gRPC call with simple error (no status details). Fallback when grpc_status unavailable."""
    import grpc as grpc_module
    code = grpc_module.StatusCode(err.grpc_code)
    context.abort(code, str(err))


def handle_grpc_error(context: grpc.ServicerContext, exc: Exception, *, default_code: int = pb.INTERNAL) -> None:
    """Convert any exception to gRPC error and abort. For use in except blocks."""
    if isinstance(exc, AppError):
        try:
            abort_with_error(context, exc)
        except ImportError:
            abort_with_error_simple(context, exc)
    else:
        err = AppError(str(exc), code=default_code, cause=exc)
        try:
            abort_with_error(context, err)
        except ImportError:
            abort_with_error_simple(context, err)


def wrap_error(exc: Exception, code: int, message: str | None = None) -> AppError:
    """Wrap a generic exception into an AppError."""
    return AppError(message or str(exc), code=code, cause=exc)


__all__ = [
    "AppError",
    "AudioError",
    "ConfigError",
    "DiarizationError",
    "ErrorCode",
    "ErrorDetails",
    "LLMError",
    "MemoryError",
    "OCRError",
    "TranscriptionError",
    "VADError",
    "abort_with_error",
    "abort_with_error_simple",
    "error_code_name",
    "handle_grpc_error",
    "wrap_error",
]
