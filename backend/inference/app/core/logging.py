"""
Core utilities: logging, configuration, and shared infrastructure.
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime


def _get_trace_context() -> tuple[str | None, str | None]:
    """Import trace module lazily to avoid circular imports."""
    try:
        from app.core.trace import get_span_id, get_trace_id

        return get_trace_id(), get_span_id()
    except ImportError:
        return None, None


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    DEBUG = "\033[36m"  # Cyan
    INFO = "\033[32m"  # Green
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"  # Red
    CRITICAL = "\033[35m"  # Magenta
    TIMESTAMP = "\033[90m"  # Gray
    NAME = "\033[34m"  # Blue
    KEY = "\033[96m"  # Light cyan
    VALUE = "\033[97m"  # White


LEVEL_COLORS = {
    "DEBUG": Colors.DEBUG,
    "INFO": Colors.INFO,
    "WARNING": Colors.WARNING,
    "ERROR": Colors.ERROR,
    "CRITICAL": Colors.CRITICAL,
}

_EXCLUDED_KEYS = {
    "name",
    "msg",
    "args",
    "created",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "exc_info",
    "exc_text",
    "thread",
    "threadName",
    "taskName",
    "message",
}


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        trace_id, span_id = _get_trace_context()
        if trace_id:
            log_data["trace_id"] = trace_id
        if span_id:
            log_data["span_id"] = span_id

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        for key in set(record.__dict__.keys()) - _EXCLUDED_KEYS:
            log_data[key] = record.__dict__[key]

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        ts_str = f"{Colors.TIMESTAMP}{ts}{Colors.RESET}"

        level_color = LEVEL_COLORS.get(record.levelname, Colors.RESET)
        level_str = f"{level_color}{record.levelname:8}{Colors.RESET}"

        name = record.name.rsplit(".", 1)[-1]
        name_str = f"{Colors.NAME}{name:15}{Colors.RESET}"

        msg = record.getMessage()

        extra_parts = []
        for key in sorted(set(record.__dict__.keys()) - _EXCLUDED_KEYS):
            val = record.__dict__[key]
            extra_parts.append(f"{Colors.KEY}{key}{Colors.RESET}={Colors.VALUE}{val}{Colors.RESET}")

        trace_id, _ = _get_trace_context()
        if trace_id:
            extra_parts.insert(0, f"{Colors.DIM}[{trace_id[:8]}]{Colors.RESET}")

        parts = [ts_str, level_str, name_str, msg]
        if extra_parts:
            parts.append(f"{Colors.DIM}│{Colors.RESET} " + " ".join(extra_parts))

        output = " ".join(parts)

        if record.exc_info:
            output += f"\n{Colors.ERROR}{self.formatException(record.exc_info)}{Colors.RESET}"

        return output


class StructuredLogger(logging.Logger):
    """Extended logger supporting structured fields."""

    def _log_with_extra(self, level: int, msg: str, *args, **kwargs) -> None:
        extra = kwargs.pop("extra", {})
        standard_keys = {"exc_info", "stack_info", "stacklevel"}
        for key in list(kwargs.keys()):
            if key not in standard_keys:
                extra[key] = kwargs.pop(key)
        kwargs["extra"] = extra
        self.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._log_with_extra(logging.CRITICAL, msg, *args, **kwargs)


logging.setLoggerClass(StructuredLogger)
_configured = False


def configure_logging(
    level: str = "INFO",
    json_output: bool | None = None,
    log_file: str | None = None,
) -> None:
    """Configure the logging system."""
    global _configured
    if _configured:
        return

    if json_output is None:
        json_output = (
            os.getenv("LOG_FORMAT", "").lower() == "json" or os.getenv("ENV", "development").lower() == "production"
        )

    level = os.getenv("LOG_LEVEL", level).upper()
    formatter = JSONFormatter() if json_output else ColoredFormatter()

    root = logging.getLogger()
    root.setLevel(getattr(logging, level))
    root.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)

    for logger_name in ["httpcore", "httpx", "urllib3", "chromadb", "onnxruntime"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    if not _configured:
        configure_logging()
    return logging.getLogger(name)  # type: ignore


# Auto-configure on import
configure_logging()

__all__ = [
    "Colors",
    "StructuredLogger",
    "configure_logging",
    "get_logger",
]
