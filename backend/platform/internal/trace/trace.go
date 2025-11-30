// Package trace provides distributed tracing with W3C Trace Context compatibility.
// Lightweight implementation without external dependencies, OTel-upgrade ready.
package trace

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"log/slog"
	"time"
)

// Metadata keys for gRPC/HTTP propagation (W3C-style).
const (
	TraceIDKey      = "x-trace-id"
	SpanIDKey       = "x-span-id"
	ParentSpanIDKey = "x-parent-span-id"
)

type ctxKey struct{}

var traceCtxKey = ctxKey{}

// Context holds trace identifiers for a single span.
type Context struct {
	TraceID      string
	SpanID       string
	ParentSpanID string
}

// New creates a new trace context with fresh IDs.
func New() Context {
	return Context{
		TraceID: generateTraceID(),
		SpanID:  generateSpanID(),
	}
}

// NewChild creates a child context from parent.
func NewChild(parent Context) Context {
	return Context{
		TraceID:      parent.TraceID,
		SpanID:       generateSpanID(),
		ParentSpanID: parent.SpanID,
	}
}

// FromContext extracts trace context from context.Context.
func FromContext(ctx context.Context) (Context, bool) {
	tc, ok := ctx.Value(traceCtxKey).(Context)
	return tc, ok
}

// WithContext injects trace context into context.Context.
func WithContext(ctx context.Context, tc Context) context.Context {
	return context.WithValue(ctx, traceCtxKey, tc)
}

// EnsureContext returns existing trace context or creates a new one.
func EnsureContext(ctx context.Context) (context.Context, Context) {
	if tc, ok := FromContext(ctx); ok {
		return ctx, tc
	}
	tc := New()
	return WithContext(ctx, tc), tc
}

// generateTraceID creates a 128-bit trace ID (W3C standard).
func generateTraceID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// generateSpanID creates a 64-bit span ID (W3C standard).
func generateSpanID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// ToMap exports context as string map for gRPC metadata.
func (c Context) ToMap() map[string]string {
	m := map[string]string{
		TraceIDKey: c.TraceID,
		SpanIDKey:  c.SpanID,
	}
	if c.ParentSpanID != "" {
		m[ParentSpanIDKey] = c.ParentSpanID
	}
	return m
}

// FromMap extracts context from string map.
func FromMap(m map[string]string) Context {
	tc := Context{
		TraceID:      m[TraceIDKey],
		SpanID:       generateSpanID(), // Always new span
		ParentSpanID: m[SpanIDKey],     // Caller's span becomes parent
	}
	if tc.TraceID == "" {
		tc.TraceID = generateTraceID()
	}
	return tc
}

// LogAttrs returns slog attributes for logging.
func (c Context) LogAttrs() []slog.Attr {
	attrs := []slog.Attr{
		slog.String("trace_id", c.TraceID),
		slog.String("span_id", c.SpanID),
	}
	if c.ParentSpanID != "" {
		attrs = append(attrs, slog.String("parent_span_id", c.ParentSpanID))
	}
	return attrs
}

// Span represents a timed operation within a trace.
type Span struct {
	Name      string
	Ctx       Context
	StartTime time.Time
	EndTime   time.Time
	Attrs     map[string]any
}

// StartSpan begins a new span.
func StartSpan(ctx context.Context, name string) (context.Context, *Span) {
	parent, _ := FromContext(ctx)
	tc := NewChild(parent)
	if parent.TraceID == "" {
		tc = New()
	}

	s := &Span{
		Name:      name,
		Ctx:       tc,
		StartTime: time.Now(),
		Attrs:     make(map[string]any),
	}
	return WithContext(ctx, tc), s
}

// End marks the span as complete.
func (s *Span) End() {
	s.EndTime = time.Now()
}

// SetAttr sets a span attribute.
func (s *Span) SetAttr(key string, val any) {
	s.Attrs[key] = val
}

// Duration returns span duration.
func (s *Span) Duration() time.Duration {
	if s.EndTime.IsZero() {
		return 0
	}
	return s.EndTime.Sub(s.StartTime)
}

// LogValue implements slog.LogValuer for structured logging.
func (s *Span) LogValue() slog.Value {
	attrs := []slog.Attr{
		slog.String("span_name", s.Name),
		slog.String("trace_id", s.Ctx.TraceID),
		slog.String("span_id", s.Ctx.SpanID),
		slog.Duration("duration", s.Duration()),
	}
	if s.Ctx.ParentSpanID != "" {
		attrs = append(attrs, slog.String("parent_span_id", s.Ctx.ParentSpanID))
	}
	for k, v := range s.Attrs {
		attrs = append(attrs, slog.Any(k, v))
	}
	return slog.GroupValue(attrs...)
}

// Logger returns a slog.Logger with trace context.
func Logger(ctx context.Context) *slog.Logger {
	tc, ok := FromContext(ctx)
	if !ok {
		return slog.Default()
	}
	args := make([]any, 0, 6)
	args = append(args, "trace_id", tc.TraceID, "span_id", tc.SpanID)
	if tc.ParentSpanID != "" {
		args = append(args, "parent_span_id", tc.ParentSpanID)
	}
	return slog.Default().With(args...)
}
