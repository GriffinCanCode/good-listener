// Package resilience provides fault tolerance patterns
package resilience

import (
	"errors"
	"log/slog"
	"sync"
	"sync/atomic"
	"time"
)

// State represents circuit breaker state.
type State uint32

const (
	Closed   State = iota // Normal operation
	Open                  // Failing fast
	HalfOpen              // Testing recovery
)

func (s State) String() string {
	return [...]string{"closed", "open", "half-open"}[s]
}

// Errors.
var (
	ErrOpen     = errors.New("circuit breaker open")
	ErrHalfOpen = errors.New("circuit breaker half-open: limiting requests")
	ErrRejected = errors.New("request rejected by circuit breaker")
)

// Breaker implements the circuit breaker pattern with sliding window and exponential backoff.
type Breaker struct {
	cfg           Config
	state         atomic.Uint32
	successes     atomic.Int32
	consecutiveOK atomic.Int32
	openedAt      atomic.Int64 // unix nano when opened
	openCount     atomic.Int32 // times opened (for backoff)
	lastLogAt     atomic.Int64 // rate limit logging
	onStateChange func(from, to State)

	// Sliding window for failure tracking
	mu       sync.Mutex
	failures []int64 // timestamps of recent failures
}

// New creates a breaker with config.
func New(cfg Config) *Breaker {
	c := cfg.withDefaults()
	return &Breaker{
		cfg:      c,
		failures: make([]int64, 0, c.Threshold),
	}
}

// WithHook sets state change callback (for metrics/logging).
func (b *Breaker) WithHook(fn func(from, to State)) *Breaker {
	b.onStateChange = fn
	return b
}

// Allow checks if request should proceed; returns nil if allowed.
func (b *Breaker) Allow() error {
	switch State(b.state.Load()) {
	case Open:
		if b.shouldAttemptReset() {
			b.transition(HalfOpen)
			return nil
		}
		b.logOpenThrottled()
		return ErrOpen
	case HalfOpen:
		return nil
	default:
		return nil
	}
}

// logOpenThrottled logs "circuit open" at most once per second to prevent log flooding.
func (b *Breaker) logOpenThrottled() {
	now := time.Now().UnixNano()
	last := b.lastLogAt.Load()
	if now-last > int64(time.Second) && b.lastLogAt.CompareAndSwap(last, now) {
		slog.Debug("circuit breaker open", "retry_after", b.timeUntilRetry())
	}
}

// timeUntilRetry returns duration until next retry attempt.
func (b *Breaker) timeUntilRetry() time.Duration {
	opened := b.openedAt.Load()
	if opened == 0 {
		return 0
	}
	backoff := b.currentBackoff()
	elapsed := time.Since(time.Unix(0, opened))
	if remaining := backoff - elapsed; remaining > 0 {
		return remaining
	}
	return 0
}

// currentBackoff returns exponential backoff duration based on open count.
func (b *Breaker) currentBackoff() time.Duration {
	count := b.openCount.Load()
	if count <= 1 {
		return b.cfg.ResetTimeout
	}
	// Exponential: base * 2^(count-1), capped at MaxBackoff
	backoff := b.cfg.ResetTimeout << min(count-1, 4)
	if backoff > b.cfg.MaxBackoff {
		return b.cfg.MaxBackoff
	}
	return backoff
}

// Success records successful call.
func (b *Breaker) Success() {
	state := State(b.state.Load())
	switch state {
	case HalfOpen:
		if b.successes.Add(1) >= int32(b.cfg.HalfOpenSuccesses) {
			b.transition(Closed)
		}
	case Closed:
		// Track consecutive successes to decay open count
		if b.consecutiveOK.Add(1) >= int32(b.cfg.Threshold*2) {
			b.openCount.Store(0) // reset backoff after sustained success
			b.consecutiveOK.Store(0)
		}
		b.clearOldFailures()
	}
}

// Failure records failed call using sliding window.
func (b *Breaker) Failure() {
	now := time.Now().UnixNano()
	b.consecutiveOK.Store(0)

	state := State(b.state.Load())
	switch state {
	case HalfOpen:
		b.transition(Open)
		return
	case Closed:
		b.mu.Lock()
		b.failures = append(b.failures, now)
		b.pruneFailures(now)
		count := len(b.failures)
		b.mu.Unlock()

		if count >= b.cfg.Threshold {
			b.transition(Open)
		}
	}
}

// pruneFailures removes failures outside the sliding window. Must hold mu.
func (b *Breaker) pruneFailures(now int64) {
	cutoff := now - int64(b.cfg.FailureWindow)
	i := 0
	for i < len(b.failures) && b.failures[i] < cutoff {
		i++
	}
	if i > 0 {
		b.failures = b.failures[i:]
	}
}

// clearOldFailures clears failures outside window on success path.
func (b *Breaker) clearOldFailures() {
	b.mu.Lock()
	b.pruneFailures(time.Now().UnixNano())
	b.mu.Unlock()
}

// State returns current state.
func (b *Breaker) State() State {
	return State(b.state.Load())
}

// Reset forces breaker to closed state.
func (b *Breaker) Reset() {
	b.transition(Closed)
	b.openCount.Store(0)
}

// transition changes state with side effects.
func (b *Breaker) transition(to State) {
	from := State(b.state.Swap(uint32(to)))
	if from == to {
		return
	}

	switch to {
	case Closed:
		b.mu.Lock()
		b.failures = b.failures[:0]
		b.mu.Unlock()
		b.successes.Store(0)
		b.consecutiveOK.Store(0)
		slog.Info("circuit breaker closed")
	case Open:
		b.successes.Store(0)
		b.openedAt.Store(time.Now().UnixNano())
		count := b.openCount.Add(1)
		slog.Warn("circuit breaker opened", "failures", b.cfg.Threshold, "backoff", b.currentBackoff(), "open_count", count)
	case HalfOpen:
		b.successes.Store(0)
		slog.Info("circuit breaker half-open", "required_successes", b.cfg.HalfOpenSuccesses)
	}

	if b.onStateChange != nil {
		b.onStateChange(from, to)
	}
}

func (b *Breaker) shouldAttemptReset() bool {
	opened := b.openedAt.Load()
	if opened == 0 {
		return true
	}
	return time.Since(time.Unix(0, opened)) > b.currentBackoff()
}

// Execute runs fn with circuit breaker protection.
func (b *Breaker) Execute(fn func() error) error {
	if err := b.Allow(); err != nil {
		return err
	}
	if err := fn(); err != nil {
		b.Failure()
		return err
	}
	b.Success()
	return nil
}

// ExecuteWithResult runs fn returning value and error with circuit protection.
func ExecuteWithResult[T any](b *Breaker, fn func() (T, error)) (T, error) {
	var zero T
	if err := b.Allow(); err != nil {
		return zero, err
	}
	result, err := fn()
	if err != nil {
		b.Failure()
		return zero, err
	}
	b.Success()
	return result, nil
}
