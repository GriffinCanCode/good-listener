package resilience

import (
	"context"
	"errors"
	"testing"
	"time"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func TestRetrySucceedsFirst(t *testing.T) {
	calls := 0
	err := Retry(context.Background(), DefaultRetryConfig(), func() error {
		calls++
		return nil
	})

	if err != nil {
		t.Errorf("Retry() = %v, want nil", err)
	}
	if calls != 1 {
		t.Errorf("calls = %d, want 1", calls)
	}
}

func TestRetrySucceedsAfterFailures(t *testing.T) {
	cfg := RetryConfig{MaxRetries: 3, BaseDelay: time.Millisecond, MaxDelay: 10 * time.Millisecond}
	calls := 0
	err := Retry(context.Background(), cfg, func() error {
		calls++
		if calls < 3 {
			return status.Error(codes.Unavailable, "transient")
		}
		return nil
	})

	if err != nil {
		t.Errorf("Retry() = %v, want nil", err)
	}
	if calls != 3 {
		t.Errorf("calls = %d, want 3", calls)
	}
}

func TestRetryExhaustsRetries(t *testing.T) {
	cfg := RetryConfig{MaxRetries: 2, BaseDelay: time.Millisecond, MaxDelay: 10 * time.Millisecond}
	calls := 0
	retryErr := status.Error(codes.Unavailable, "always fail")

	err := Retry(context.Background(), cfg, func() error {
		calls++
		return retryErr
	})

	if !errors.Is(err, retryErr) {
		t.Errorf("Retry() = %v, want %v", err, retryErr)
	}
	if calls != 3 { // initial + 2 retries
		t.Errorf("calls = %d, want 3", calls)
	}
}

func TestRetryNonRetryableError(t *testing.T) {
	cfg := RetryConfig{MaxRetries: 5, BaseDelay: time.Millisecond, MaxDelay: 10 * time.Millisecond}
	calls := 0
	nonRetryErr := status.Error(codes.InvalidArgument, "bad request")

	err := Retry(context.Background(), cfg, func() error {
		calls++
		return nonRetryErr
	})

	if !errors.Is(err, nonRetryErr) {
		t.Errorf("Retry() = %v, want %v", err, nonRetryErr)
	}
	if calls != 1 { // Should not retry non-retryable errors
		t.Errorf("calls = %d, want 1", calls)
	}
}

func TestRetryContextCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cfg := RetryConfig{MaxRetries: 10, BaseDelay: 100 * time.Millisecond, MaxDelay: time.Second}
	calls := 0

	go func() {
		time.Sleep(50 * time.Millisecond)
		cancel()
	}()

	err := Retry(ctx, cfg, func() error {
		calls++
		return status.Error(codes.Unavailable, "fail")
	})

	if !errors.Is(err, context.Canceled) {
		t.Errorf("Retry() = %v, want context.Canceled", err)
	}
}

func TestIsRetryableGRPC(t *testing.T) {
	tests := []struct {
		code codes.Code
		want bool
	}{
		{codes.Unavailable, true},
		{codes.DeadlineExceeded, true},
		{codes.ResourceExhausted, true},
		{codes.Aborted, true},
		{codes.Internal, true},
		{codes.InvalidArgument, false},
		{codes.NotFound, false},
		{codes.PermissionDenied, false},
		{codes.OK, false},
	}

	for _, tt := range tests {
		err := status.Error(tt.code, "test")
		if got := IsRetryableGRPC(err); got != tt.want {
			t.Errorf("IsRetryableGRPC(%v) = %v, want %v", tt.code, got, tt.want)
		}
	}
}

func TestLLMRetryConfig(t *testing.T) {
	cfg := LLMRetryConfig()
	if cfg.MaxRetries != LLMMaxRetries {
		t.Errorf("MaxRetries = %d, want %d", cfg.MaxRetries, LLMMaxRetries)
	}
	if cfg.BaseDelay != LLMBaseDelay {
		t.Errorf("BaseDelay = %v, want %v", cfg.BaseDelay, LLMBaseDelay)
	}
	if cfg.MaxDelay != LLMMaxDelay {
		t.Errorf("MaxDelay = %v, want %v", cfg.MaxDelay, LLMMaxDelay)
	}
}

func TestBackoffDelay(t *testing.T) {
	cfg := RetryConfig{BaseDelay: 100 * time.Millisecond, MaxDelay: time.Second, JitterFactor: 0}

	d0 := backoffDelay(cfg, 0)
	d1 := backoffDelay(cfg, 1)
	d2 := backoffDelay(cfg, 2)

	if d0 != 100*time.Millisecond {
		t.Errorf("attempt 0 delay = %v, want 100ms", d0)
	}
	if d1 != 200*time.Millisecond {
		t.Errorf("attempt 1 delay = %v, want 200ms", d1)
	}
	if d2 != 400*time.Millisecond {
		t.Errorf("attempt 2 delay = %v, want 400ms", d2)
	}
}

func TestBackoffDelayCapped(t *testing.T) {
	cfg := RetryConfig{BaseDelay: 100 * time.Millisecond, MaxDelay: 300 * time.Millisecond, JitterFactor: 0}

	d5 := backoffDelay(cfg, 5)
	if d5 != 300*time.Millisecond {
		t.Errorf("attempt 5 delay = %v, want 300ms (capped)", d5)
	}
}
