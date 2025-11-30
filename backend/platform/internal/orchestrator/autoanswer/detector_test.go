package autoanswer

import (
	"context"
	"testing"
	"time"
)

type mockDetector struct {
	isQuestion bool
	err        error
	calls      int
}

func (m *mockDetector) IsQuestion(_ context.Context, _ string) (bool, error) {
	m.calls++
	return m.isQuestion, m.err
}

func TestDetectorDisabled(t *testing.T) {
	mock := &mockDetector{isQuestion: true}
	d := NewDetector(mock, 10, false)

	if d.Check(context.Background(), "Is this a question?") {
		t.Error("disabled detector should return false")
	}
	if mock.calls != 0 {
		t.Error("should not call detector when disabled")
	}
}

func TestDetectorEnabled(t *testing.T) {
	mock := &mockDetector{isQuestion: true}
	d := NewDetector(mock, 10, true)

	if !d.Check(context.Background(), "Is this a question?") {
		t.Error("should return true for question")
	}
	if mock.calls != 1 {
		t.Errorf("expected 1 call, got %d", mock.calls)
	}
}

func TestDetectorNotQuestion(t *testing.T) {
	mock := &mockDetector{isQuestion: false}
	d := NewDetector(mock, 10, true)

	if d.Check(context.Background(), "This is a statement.") {
		t.Error("should return false for non-question")
	}
}

func TestDetectorCooldown(t *testing.T) {
	mock := &mockDetector{isQuestion: true}
	d := NewDetector(mock, 1, true) // 1 second cooldown

	// First check should succeed
	if !d.Check(context.Background(), "Question 1?") {
		t.Error("first check should succeed")
	}

	// Immediate second check should fail (cooldown)
	if d.Check(context.Background(), "Question 2?") {
		t.Error("should be in cooldown")
	}

	// Wait for cooldown
	time.Sleep(1100 * time.Millisecond)

	// Should work again
	if !d.Check(context.Background(), "Question 3?") {
		t.Error("should work after cooldown")
	}
}

func TestSetEnabled(t *testing.T) {
	mock := &mockDetector{}
	d := NewDetector(mock, 10, false)

	if d.IsEnabled() {
		t.Error("should be disabled initially")
	}

	d.SetEnabled(true)
	if !d.IsEnabled() {
		t.Error("should be enabled after SetEnabled(true)")
	}

	d.SetEnabled(false)
	if d.IsEnabled() {
		t.Error("should be disabled after SetEnabled(false)")
	}
}
