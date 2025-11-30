"""Tests for distributed tracing module."""

import pytest
from unittest.mock import MagicMock

from app.core.trace import (
    TraceContext,
    Span,
    span,
    traced,
    generate_trace_id,
    generate_span_id,
    set_trace_context,
    get_trace_id,
    get_span_id,
    clear_trace_context,
    TRACE_ID_KEY,
    SPAN_ID_KEY,
)


class TestTraceIdGeneration:
    """Test trace and span ID generation."""
    
    def test_trace_id_length(self):
        """Trace ID should be 32 hex chars (128 bits)."""
        tid = generate_trace_id()
        assert len(tid) == 32
        assert all(c in "0123456789abcdef" for c in tid)
    
    def test_span_id_length(self):
        """Span ID should be 16 hex chars (64 bits)."""
        sid = generate_span_id()
        assert len(sid) == 16
        assert all(c in "0123456789abcdef" for c in sid)
    
    def test_ids_unique(self):
        """Each generated ID should be unique."""
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100


class TestTraceContext:
    """Test TraceContext creation and propagation."""
    
    def test_new_context(self):
        """New context should have trace_id and span_id."""
        ctx = TraceContext.new()
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16
        assert ctx.parent_span_id is None
    
    def test_child_context(self):
        """Child context should inherit trace_id, have new span_id, parent = old span."""
        parent = TraceContext.new()
        child = TraceContext.new(parent)
        
        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id
        assert child.parent_span_id == parent.span_id
    
    def test_from_grpc_context(self):
        """Should extract trace context from gRPC metadata."""
        mock_ctx = MagicMock()
        mock_ctx.invocation_metadata.return_value = [
            (TRACE_ID_KEY, "a" * 32),
            (SPAN_ID_KEY, "b" * 16),
        ]
        
        ctx = TraceContext.from_grpc_context(mock_ctx)
        assert ctx.trace_id == "a" * 32
        assert ctx.parent_span_id == "b" * 16
        assert len(ctx.span_id) == 16  # New span for this service
    
    def test_from_grpc_generates_trace_if_missing(self):
        """Should generate trace_id if not in metadata."""
        mock_ctx = MagicMock()
        mock_ctx.invocation_metadata.return_value = []
        
        ctx = TraceContext.from_grpc_context(mock_ctx)
        assert len(ctx.trace_id) == 32
    
    def test_to_dict(self):
        """Should export as dict for logging."""
        ctx = TraceContext("trace123", "span456", "parent789")
        d = ctx.to_dict()
        
        assert d["trace_id"] == "trace123"
        assert d["span_id"] == "span456"
        assert d["parent_span_id"] == "parent789"
    
    def test_to_dict_no_parent(self):
        """Should omit parent_span_id if None."""
        ctx = TraceContext("trace123", "span456")
        d = ctx.to_dict()
        
        assert "parent_span_id" not in d


class TestContextVars:
    """Test contextvar-based trace propagation."""
    
    def setup_method(self):
        """Clear trace context before each test."""
        clear_trace_context()
    
    def test_set_and_get_trace_context(self):
        """Should store and retrieve trace context."""
        ctx = TraceContext.new()
        set_trace_context(ctx)
        
        assert get_trace_id() == ctx.trace_id
        assert get_span_id() == ctx.span_id
    
    def test_current_returns_context(self):
        """TraceContext.current() should return stored context."""
        ctx = TraceContext.new()
        set_trace_context(ctx)
        
        current = TraceContext.current()
        assert current is not None
        assert current.trace_id == ctx.trace_id
    
    def test_current_returns_none_if_not_set(self):
        """TraceContext.current() should return None if not set."""
        assert TraceContext.current() is None


class TestSpan:
    """Test span timing and attributes."""
    
    def test_span_timing(self):
        """Span should track duration."""
        with span("test_op") as s:
            pass  # Quick operation
        
        assert s.duration_ms >= 0
        assert s.end_ns is not None
    
    def test_span_attributes(self):
        """Span should store attributes."""
        with span("test_op", key1="val1", key2=42) as s:
            pass
        
        assert s.attributes["key1"] == "val1"
        assert s.attributes["key2"] == 42
    
    def test_span_to_dict(self):
        """Span.to_dict() should include all info."""
        with span("my_span") as s:
            pass
        
        d = s.to_dict()
        assert "trace_id" in d
        assert "span_id" in d
        assert d["span_name"] == "my_span"
        assert "duration_ms" in d


class TestTracedDecorator:
    """Test @traced decorator."""
    
    def setup_method(self):
        clear_trace_context()
    
    def test_traced_sync_function(self):
        """@traced should wrap sync functions."""
        @traced("my_func")
        def my_func(x: int) -> int:
            return x * 2
        
        result = my_func(5)
        assert result == 10
    
    def test_traced_preserves_exception(self):
        """@traced should re-raise exceptions."""
        @traced()
        def failing_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError, match="test error"):
            failing_func()
    
    @pytest.mark.asyncio
    async def test_traced_async_function(self):
        """@traced should wrap async functions."""
        @traced("async_op")
        async def async_op(x: int) -> int:
            return x + 1
        
        result = await async_op(10)
        assert result == 11

