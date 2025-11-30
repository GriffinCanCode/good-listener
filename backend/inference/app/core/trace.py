"""
Distributed tracing with W3C Trace Context compatibility.

Provides lightweight tracing across service boundaries without external dependencies.
Compatible with OpenTelemetry for future upgrade path.
"""

import secrets
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable, TypeVar, ParamSpec
from functools import wraps

import grpc

# Context variables for async-safe trace propagation
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_parent_span_id: ContextVar[str | None] = ContextVar("parent_span_id", default=None)

# gRPC metadata keys (W3C-style)
TRACE_ID_KEY = "x-trace-id"
SPAN_ID_KEY = "x-span-id"
PARENT_SPAN_ID_KEY = "x-parent-span-id"


def generate_trace_id() -> str:
    """Generate 128-bit trace ID (W3C standard)."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generate 64-bit span ID (W3C standard)."""
    return secrets.token_hex(8)


@dataclass(slots=True, frozen=True)
class TraceContext:
    """Immutable trace context for a single span."""
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    
    @classmethod
    def new(cls, parent: "TraceContext | None" = None) -> "TraceContext":
        """Create new context, optionally as child of parent."""
        if parent:
            return cls(parent.trace_id, generate_span_id(), parent.span_id)
        return cls(generate_trace_id(), generate_span_id())
    
    @classmethod
    def current(cls) -> "TraceContext | None":
        """Get current trace context from contextvars."""
        tid = _trace_id.get()
        if not tid:
            return None
        return cls(tid, _span_id.get() or generate_span_id(), _parent_span_id.get())
    
    @classmethod
    def from_grpc_context(cls, context: grpc.ServicerContext) -> "TraceContext":
        """Extract trace context from gRPC metadata."""
        meta = dict(context.invocation_metadata() or [])
        trace_id = meta.get(TRACE_ID_KEY) or generate_trace_id()
        span_id = generate_span_id()  # Always new span for this service
        parent = meta.get(SPAN_ID_KEY)  # Caller's span becomes our parent
        return cls(trace_id, span_id, parent)
    
    def to_dict(self) -> dict[str, str]:
        """Export as dict for logging/serialization."""
        d = {"trace_id": self.trace_id, "span_id": self.span_id}
        if self.parent_span_id:
            d["parent_span_id"] = self.parent_span_id
        return d


def set_trace_context(ctx: TraceContext) -> None:
    """Set trace context in contextvars (for current async context)."""
    _trace_id.set(ctx.trace_id)
    _span_id.set(ctx.span_id)
    _parent_span_id.set(ctx.parent_span_id)


def clear_trace_context() -> None:
    """Clear trace context from contextvars."""
    _trace_id.set(None)
    _span_id.set(None)
    _parent_span_id.set(None)


def get_trace_id() -> str | None:
    """Get current trace ID."""
    return _trace_id.get()


def get_span_id() -> str | None:
    """Get current span ID."""
    return _span_id.get()


@dataclass
class Span:
    """A timed span for performance tracking."""
    name: str
    ctx: TraceContext
    start_ns: int = field(default_factory=time.perf_counter_ns)
    end_ns: int | None = None
    attributes: dict[str, str | int | float] = field(default_factory=dict)
    
    def end(self) -> None:
        """Mark span as complete."""
        self.end_ns = time.perf_counter_ns()
    
    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        if self.end_ns is None:
            return 0.0
        return (self.end_ns - self.start_ns) / 1_000_000
    
    def to_dict(self) -> dict:
        """Export span data for logging."""
        return {
            **self.ctx.to_dict(),
            "span_name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            **self.attributes,
        }


class SpanManager:
    """Context manager for span lifecycle."""
    
    def __init__(self, name: str, parent_ctx: TraceContext | None = None, **attrs):
        self.name = name
        self.parent_ctx = parent_ctx or TraceContext.current()
        self.attrs = attrs
        self.span: Span | None = None
    
    def __enter__(self) -> Span:
        ctx = TraceContext.new(self.parent_ctx)
        set_trace_context(ctx)
        self.span = Span(self.name, ctx, attributes=self.attrs)
        return self.span
    
    def __exit__(self, *_) -> None:
        if self.span:
            self.span.end()


def span(name: str, **attrs):
    """Create a span context manager."""
    return SpanManager(name, **attrs)


# gRPC Server Interceptor
class TracingInterceptor(grpc.aio.ServerInterceptor):
    """gRPC server interceptor that extracts trace context from metadata."""
    
    async def intercept_service(self, continuation, handler_call_details):
        # Extract metadata
        meta = dict(handler_call_details.invocation_metadata or [])
        
        # Create trace context
        trace_id = meta.get(TRACE_ID_KEY) or generate_trace_id()
        parent_span = meta.get(SPAN_ID_KEY)
        ctx = TraceContext(trace_id, generate_span_id(), parent_span)
        set_trace_context(ctx)
        
        return await continuation(handler_call_details)


P = ParamSpec("P")
T = TypeVar("T")


def traced(name: str | None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to trace a function execution."""
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        span_name = name or fn.__name__
        
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with span(span_name) as s:
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    s.attributes["error"] = str(e)
                    raise
        
        @wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with span(span_name) as s:
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    s.attributes["error"] = str(e)
                    raise
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(fn) else wrapper
    return decorator


__all__ = [
    "TraceContext",
    "Span",
    "span",
    "traced",
    "get_trace_id",
    "get_span_id",
    "set_trace_context",
    "clear_trace_context",
    "generate_trace_id",
    "generate_span_id",
    "TracingInterceptor",
    "TRACE_ID_KEY",
    "SPAN_ID_KEY",
    "PARENT_SPAN_ID_KEY",
]

