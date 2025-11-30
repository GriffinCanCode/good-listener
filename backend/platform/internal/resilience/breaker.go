// Package resilience provides fault tolerance patterns
package resilience

import (
	"errors"
	"log/slog"
	"sync/atomic"
	"time"
)

// State represents circuit breaker state
type State uint32

const (
	Closed   State = iota // Normal operation
	Open                  // Failing fast
	HalfOpen              // Testing recovery
)

func (s State) String() string {
	return [...]string{"closed", "open", "half-open"}[s]
}

// Errors
var (
	ErrOpen      = errors.New("circuit breaker open")
	ErrHalfOpen  = errors.New("circuit breaker half-open: limiting requests")
	ErrRejected  = errors.New("request rejected by circuit breaker")
)

// Breaker implements the circuit breaker pattern with atomic state
type Breaker struct {
	cfg         Config
	state       atomic.Uint32
	failures    atomic.Int32
	successes   atomic.Int32
	lastFailure atomic.Int64 // unix nano
	onStateChange func(from, to State)
}

// New creates a breaker with config
func New(cfg Config) *Breaker {
	b := &Breaker{cfg: cfg.withDefaults()}
	b.state.Store(uint32(Closed))
	return b
}

// WithHook sets state change callback (for metrics/logging)
func (b *Breaker) WithHook(fn func(from, to State)) *Breaker {
	b.onStateChange = fn
	return b
}

// Allow checks if request should proceed; returns nil if allowed
func (b *Breaker) Allow() error {
	switch State(b.state.Load()) {
	case Open:
		if b.shouldAttemptReset() {
			b.transition(HalfOpen)
			return nil
		}
		return ErrOpen
	case HalfOpen:
		// Allow limited requests in half-open
		return nil
	default:
		return nil
	}
}

// Success records successful call
func (b *Breaker) Success() {
	switch State(b.state.Load()) {
	case HalfOpen:
		if b.successes.Add(1) >= int32(b.cfg.HalfOpenSuccesses) {
			b.transition(Closed)
		}
	case Closed:
		// Reset failure count on success in closed state
		b.failures.Store(0)
	}
}

// Failure records failed call
func (b *Breaker) Failure() {
	b.lastFailure.Store(time.Now().UnixNano())
	count := b.failures.Add(1)

	switch State(b.state.Load()) {
	case HalfOpen:
		b.transition(Open)
	case Closed:
		if count >= int32(b.cfg.Threshold) {
			b.transition(Open)
		}
	}
}

// State returns current state
func (b *Breaker) State() State {
	return State(b.state.Load())
}

// Reset forces breaker to closed state
func (b *Breaker) Reset() {
	b.transition(Closed)
}

// transition changes state with side effects
func (b *Breaker) transition(to State) {
	from := State(b.state.Swap(uint32(to)))
	if from == to {
		return
	}

	// Reset counters on transition
	switch to {
	case Closed:
		b.failures.Store(0)
		b.successes.Store(0)
		slog.Info("circuit breaker closed")
	case Open:
		b.successes.Store(0)
		slog.Warn("circuit breaker opened", "failures", b.failures.Load())
	case HalfOpen:
		b.successes.Store(0)
		slog.Info("circuit breaker half-open")
	}

	if b.onStateChange != nil {
		b.onStateChange(from, to)
	}
}

func (b *Breaker) shouldAttemptReset() bool {
	last := b.lastFailure.Load()
	if last == 0 {
		return true
	}
	return time.Since(time.Unix(0, last)) > b.cfg.ResetTimeout
}

// Execute runs fn with circuit breaker protection
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

// ExecuteWithResult runs fn returning value and error with circuit protection
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

