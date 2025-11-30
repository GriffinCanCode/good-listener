package trace

import (
	"context"
	"testing"
)

func TestGenerateTraceID(t *testing.T) {
	id := generateTraceID()
	if len(id) != 32 {
		t.Errorf("trace ID should be 32 chars, got %d", len(id))
	}
}

func TestGenerateSpanID(t *testing.T) {
	id := generateSpanID()
	if len(id) != 16 {
		t.Errorf("span ID should be 16 chars, got %d", len(id))
	}
}

func TestIDsUnique(t *testing.T) {
	seen := make(map[string]bool)
	for i := 0; i < 100; i++ {
		id := generateTraceID()
		if seen[id] {
			t.Error("generated duplicate trace ID")
		}
		seen[id] = true
	}
}

func TestNewContext(t *testing.T) {
	ctx := New()
	if len(ctx.TraceID) != 32 {
		t.Errorf("trace ID should be 32 chars, got %d", len(ctx.TraceID))
	}
	if len(ctx.SpanID) != 16 {
		t.Errorf("span ID should be 16 chars, got %d", len(ctx.SpanID))
	}
	if ctx.ParentSpanID != "" {
		t.Error("new context should not have parent span ID")
	}
}

func TestNewChild(t *testing.T) {
	parent := New()
	child := NewChild(parent)

	if child.TraceID != parent.TraceID {
		t.Error("child should inherit trace ID")
	}
	if child.SpanID == parent.SpanID {
		t.Error("child should have new span ID")
	}
	if child.ParentSpanID != parent.SpanID {
		t.Error("child's parent should be parent's span ID")
	}
}

func TestContextPropagation(t *testing.T) {
	tc := New()
	ctx := WithContext(context.Background(), tc)

	extracted, ok := FromContext(ctx)
	if !ok {
		t.Fatal("should extract trace context")
	}
	if extracted.TraceID != tc.TraceID {
		t.Error("extracted trace ID mismatch")
	}
}

func TestFromContextMissing(t *testing.T) {
	_, ok := FromContext(context.Background())
	if ok {
		t.Error("should not find trace context in empty context")
	}
}

func TestEnsureContext(t *testing.T) {
	// Empty context should create new trace
	ctx, tc := EnsureContext(context.Background())
	if len(tc.TraceID) != 32 {
		t.Error("should create trace ID")
	}

	// Context with trace should return existing
	ctx2, tc2 := EnsureContext(ctx)
	if tc2.TraceID != tc.TraceID {
		t.Error("should return existing trace")
	}
	_ = ctx2
}

func TestToMap(t *testing.T) {
	tc := Context{
		TraceID:      "trace123",
		SpanID:       "span456",
		ParentSpanID: "parent789",
	}
	m := tc.ToMap()

	if m[TraceIDKey] != "trace123" {
		t.Error("trace ID mismatch")
	}
	if m[SpanIDKey] != "span456" {
		t.Error("span ID mismatch")
	}
	if m[ParentSpanIDKey] != "parent789" {
		t.Error("parent span ID mismatch")
	}
}

func TestFromMap(t *testing.T) {
	m := map[string]string{
		TraceIDKey: "trace123",
		SpanIDKey:  "span456",
	}
	tc := FromMap(m)

	if tc.TraceID != "trace123" {
		t.Error("trace ID mismatch")
	}
	if tc.ParentSpanID != "span456" {
		t.Error("parent span should be caller's span")
	}
	if len(tc.SpanID) != 16 {
		t.Error("should generate new span ID")
	}
}

func TestFromMapGeneratesTrace(t *testing.T) {
	tc := FromMap(map[string]string{})
	if len(tc.TraceID) != 32 {
		t.Error("should generate trace ID if missing")
	}
}

func TestStartSpan(t *testing.T) {
	ctx := context.Background()
	ctx, span := StartSpan(ctx, "test_span")

	if span.Name != "test_span" {
		t.Error("span name mismatch")
	}
	if span.StartTime.IsZero() {
		t.Error("span should have start time")
	}

	span.SetAttr("key", "value")
	span.End()

	if span.EndTime.IsZero() {
		t.Error("span should have end time")
	}
	if span.Duration() <= 0 {
		t.Error("span should have positive duration")
	}
	if span.Attrs["key"] != "value" {
		t.Error("span attribute mismatch")
	}
}

func TestSpanNested(t *testing.T) {
	ctx := context.Background()
	ctx, parent := StartSpan(ctx, "parent")
	ctx, child := StartSpan(ctx, "child")

	if child.Ctx.TraceID != parent.Ctx.TraceID {
		t.Error("child should inherit trace ID")
	}
	if child.Ctx.ParentSpanID != parent.Ctx.SpanID {
		t.Error("child's parent should be parent's span")
	}
	_ = ctx
}

func TestLogger(t *testing.T) {
	tc := New()
	ctx := WithContext(context.Background(), tc)
	log := Logger(ctx)

	// Just verify it doesn't panic and returns a logger
	log.Info("test message")
}
