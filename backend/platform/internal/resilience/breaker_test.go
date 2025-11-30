package resilience

import (
	"errors"
	"sync"
	"testing"
	"time"
)

func TestBreakerInitialState(t *testing.T) {
	b := New(DefaultConfig())
	if b.State() != Closed {
		t.Errorf("initial state = %v, want Closed", b.State())
	}
}

func TestBreakerOpensAfterThreshold(t *testing.T) {
	b := New(Config{Threshold: 3, ResetTimeout: time.Hour, HalfOpenSuccesses: 2})

	for i := 0; i < 3; i++ {
		b.Failure()
	}

	if b.State() != Open {
		t.Errorf("state = %v, want Open", b.State())
	}
}

func TestBreakerRejectsWhenOpen(t *testing.T) {
	b := New(Config{Threshold: 1, ResetTimeout: time.Hour, HalfOpenSuccesses: 1})
	b.Failure()

	if err := b.Allow(); err != ErrOpen {
		t.Errorf("Allow() = %v, want ErrOpen", err)
	}
}

func TestBreakerTransitionsToHalfOpen(t *testing.T) {
	b := New(Config{Threshold: 1, ResetTimeout: time.Millisecond, HalfOpenSuccesses: 1})
	b.Failure()

	time.Sleep(5 * time.Millisecond)

	if err := b.Allow(); err != nil {
		t.Errorf("Allow() = %v, want nil", err)
	}
	if b.State() != HalfOpen {
		t.Errorf("state = %v, want HalfOpen", b.State())
	}
}

func TestBreakerClosesAfterSuccesses(t *testing.T) {
	b := New(Config{Threshold: 1, ResetTimeout: time.Millisecond, HalfOpenSuccesses: 2})
	b.Failure()

	time.Sleep(5 * time.Millisecond)
	_ = b.Allow() // transition to half-open

	b.Success()
	b.Success()

	if b.State() != Closed {
		t.Errorf("state = %v, want Closed", b.State())
	}
}

func TestBreakerReopensOnHalfOpenFailure(t *testing.T) {
	b := New(Config{Threshold: 1, ResetTimeout: time.Millisecond, HalfOpenSuccesses: 3})
	b.Failure()

	time.Sleep(5 * time.Millisecond)
	_ = b.Allow() // transition to half-open

	b.Failure()

	if b.State() != Open {
		t.Errorf("state = %v, want Open", b.State())
	}
}

func TestBreakerReset(t *testing.T) {
	b := New(Config{Threshold: 1, ResetTimeout: time.Hour, HalfOpenSuccesses: 1})
	b.Failure()

	if b.State() != Open {
		t.Fatal("expected open state")
	}

	b.Reset()

	if b.State() != Closed {
		t.Errorf("state = %v, want Closed", b.State())
	}
}

func TestBreakerExecute(t *testing.T) {
	b := New(Config{Threshold: 2, ResetTimeout: time.Second, HalfOpenSuccesses: 1})

	// Success case
	err := b.Execute(func() error { return nil })
	if err != nil {
		t.Errorf("Execute success = %v, want nil", err)
	}

	// Failure case
	testErr := errors.New("test error")
	err = b.Execute(func() error { return testErr })
	if err != testErr {
		t.Errorf("Execute failure = %v, want %v", err, testErr)
	}
}

func TestBreakerExecuteWithResult(t *testing.T) {
	b := New(DefaultConfig())

	result, err := ExecuteWithResult(b, func() (int, error) {
		return 42, nil
	})
	if err != nil || result != 42 {
		t.Errorf("ExecuteWithResult = (%d, %v), want (42, nil)", result, err)
	}
}

func TestBreakerHook(t *testing.T) {
	var transitions []struct{ from, to State }
	b := New(Config{Threshold: 1, ResetTimeout: time.Millisecond, HalfOpenSuccesses: 1})
	b.WithHook(func(from, to State) {
		transitions = append(transitions, struct{ from, to State }{from, to})
	})

	b.Failure()
	time.Sleep(5 * time.Millisecond)
	_ = b.Allow()
	b.Success()

	if len(transitions) != 3 {
		t.Errorf("got %d transitions, want 3", len(transitions))
	}
}

func TestBreakerConcurrentSafety(t *testing.T) {
	b := New(Config{Threshold: 100, ResetTimeout: time.Second, HalfOpenSuccesses: 10})

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_ = b.Allow()
			if i%2 == 0 {
				b.Success()
			} else {
				b.Failure()
			}
		}()
	}
	wg.Wait()

	// Just verify no race conditions - state is valid
	_ = b.State()
}

func TestStateString(t *testing.T) {
	tests := []struct {
		s    State
		want string
	}{
		{Closed, "closed"},
		{Open, "open"},
		{HalfOpen, "half-open"},
	}

	for _, tt := range tests {
		if got := tt.s.String(); got != tt.want {
			t.Errorf("State(%d).String() = %q, want %q", tt.s, got, tt.want)
		}
	}
}

func TestConfigDefaults(t *testing.T) {
	cfg := Config{}.withDefaults()

	if cfg.Threshold != 5 {
		t.Errorf("Threshold = %d, want 5", cfg.Threshold)
	}
	if cfg.ResetTimeout != 30*time.Second {
		t.Errorf("ResetTimeout = %v, want 30s", cfg.ResetTimeout)
	}
	if cfg.HalfOpenSuccesses != 3 {
		t.Errorf("HalfOpenSuccesses = %d, want 3", cfg.HalfOpenSuccesses)
	}
}

func TestSuccessResetsFailures(t *testing.T) {
	b := New(Config{Threshold: 3, ResetTimeout: time.Hour, HalfOpenSuccesses: 1})

	b.Failure()
	b.Failure()
	b.Success() // Should reset failure count
	b.Failure()
	b.Failure()

	// Should still be closed since successes reset the count
	if b.State() != Closed {
		t.Errorf("state = %v, want Closed", b.State())
	}
}
