// Package resilience provides fault tolerance patterns
package resilience

import (
	"context"
	"log/slog"
	"math/rand/v2"
	"time"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// Retry configuration constants
const (
	DefaultMaxRetries   = 3
	DefaultBaseDelay    = 500 * time.Millisecond
	DefaultMaxDelay     = 10 * time.Second
	DefaultJitterFactor = 0.2 // 20% jitter

	// LLM-specific: more retries, longer delays for flaky APIs
	LLMMaxRetries = 5
	LLMBaseDelay  = 1 * time.Second
	LLMMaxDelay   = 30 * time.Second
)

// RetryConfig holds retry settings.
type RetryConfig struct {
	MaxRetries   int
	BaseDelay    time.Duration
	MaxDelay     time.Duration
	JitterFactor float64
	IsRetryable  func(error) bool
}

// DefaultRetryConfig returns standard retry settings.
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxRetries:   DefaultMaxRetries,
		BaseDelay:    DefaultBaseDelay,
		MaxDelay:     DefaultMaxDelay,
		JitterFactor: DefaultJitterFactor,
		IsRetryable:  IsRetryableGRPC,
	}
}

// LLMRetryConfig returns settings optimized for flaky LLM APIs.
func LLMRetryConfig() RetryConfig {
	return RetryConfig{
		MaxRetries:   LLMMaxRetries,
		BaseDelay:    LLMBaseDelay,
		MaxDelay:     LLMMaxDelay,
		JitterFactor: DefaultJitterFactor,
		IsRetryable:  IsRetryableGRPC,
	}
}

// IsRetryableGRPC checks if a gRPC error is worth retrying.
func IsRetryableGRPC(err error) bool {
	if err == nil {
		return false
	}
	s, ok := status.FromError(err)
	if !ok {
		return true // Non-gRPC error, retry
	}
	switch s.Code() {
	case codes.Unavailable, codes.DeadlineExceeded, codes.ResourceExhausted, codes.Aborted, codes.Internal:
		return true
	default:
		return false
	}
}

// Retry executes fn with exponential backoff. Returns last error if all retries fail.
func Retry(ctx context.Context, cfg RetryConfig, fn func() error) error {
	cfg = cfg.withDefaults()
	var lastErr error

	for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
		if err := ctx.Err(); err != nil {
			return err
		}

		if lastErr = fn(); lastErr == nil {
			return nil
		}

		if !cfg.IsRetryable(lastErr) || attempt == cfg.MaxRetries {
			return lastErr
		}

		delay := backoffDelay(cfg, attempt)
		slog.Debug("retrying after error", "attempt", attempt+1, "max", cfg.MaxRetries, "delay", delay, "error", lastErr)

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
		}
	}
	return lastErr
}

// backoffDelay calculates exponential backoff with jitter.
func backoffDelay(cfg RetryConfig, attempt int) time.Duration {
	delay := cfg.BaseDelay << min(attempt, 6) // Cap shift to prevent overflow
	if delay > cfg.MaxDelay {
		delay = cfg.MaxDelay
	}
	// Add jitter: delay * (1 ± jitterFactor/2)
	jitter := float64(delay) * cfg.JitterFactor * (rand.Float64() - 0.5)
	return time.Duration(float64(delay) + jitter)
}

func (c RetryConfig) withDefaults() RetryConfig {
	if c.MaxRetries <= 0 {
		c.MaxRetries = DefaultMaxRetries
	}
	if c.BaseDelay <= 0 {
		c.BaseDelay = DefaultBaseDelay
	}
	if c.MaxDelay <= 0 {
		c.MaxDelay = DefaultMaxDelay
	}
	if c.JitterFactor <= 0 {
		c.JitterFactor = DefaultJitterFactor
	}
	if c.IsRetryable == nil {
		c.IsRetryable = IsRetryableGRPC
	}
	return c
}
