package resilience

import (
	"errors"
	"sync"
	"testing"
	"time"
)

// testConfig returns a fast config for testing (short windows).
func testConfig(threshold int) Config {
	return Config{
		Threshold:         threshold,
		ResetTimeout:      time.Millisecond,
		MaxBackoff:        10 * time.Millisecond,
		FailureWindow:     time.Hour, // long window so failures don't expire in tests
		HalfOpenSuccesses: 1,
	}
}

func TestBreakerInitialState(t *testing.T) {
	b := New(DefaultConfig())
	if b.State() != Closed {
		t.Errorf("initial state = %v, want Closed", b.State())
	}
}

func TestBreakerOpensAfterThreshold(t *testing.T) {
	b := New(testConfig(3))

	for i := 0; i < 3; i++ {
		b.Failure()
	}

	if b.State() != Open {
		t.Errorf("state = %v, want Open", b.State())
	}
}

func TestBreakerRejectsWhenOpen(t *testing.T) {
	cfg := testConfig(1)
	cfg.ResetTimeout = time.Hour // prevent auto-recovery
	b := New(cfg)
	b.Failure()

	if err := b.Allow(); !errors.Is(err, ErrOpen) {
		t.Errorf("Allow() = %v, want ErrOpen", err)
	}
}

func TestBreakerTransitionsToHalfOpen(t *testing.T) {
	b := New(testConfig(1))
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
	cfg := testConfig(1)
	cfg.HalfOpenSuccesses = 2
	b := New(cfg)
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
	cfg := testConfig(1)
	cfg.HalfOpenSuccesses = 3
	b := New(cfg)
	b.Failure()

	time.Sleep(5 * time.Millisecond)
	_ = b.Allow() // transition to half-open

	b.Failure()

	if b.State() != Open {
		t.Errorf("state = %v, want Open", b.State())
	}
}

func TestBreakerReset(t *testing.T) {
	cfg := testConfig(1)
	cfg.ResetTimeout = time.Hour
	b := New(cfg)
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
	b := New(testConfig(5))

	// Success case
	err := b.Execute(func() error { return nil })
	if err != nil {
		t.Errorf("Execute success = %v, want nil", err)
	}

	// Failure case
	testErr := errors.New("test error")
	err = b.Execute(func() error { return testErr })
	if !errors.Is(err, testErr) {
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
	b := New(testConfig(1))
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
	b := New(testConfig(100))

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			_ = b.Allow()
			if n%2 == 0 {
				b.Success()
			} else {
				b.Failure()
			}
		}(i)
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

	if cfg.Threshold != DefaultThreshold {
		t.Errorf("Threshold = %d, want %d", cfg.Threshold, DefaultThreshold)
	}
	if cfg.ResetTimeout != DefaultResetTimeout {
		t.Errorf("ResetTimeout = %v, want %v", cfg.ResetTimeout, DefaultResetTimeout)
	}
	if cfg.HalfOpenSuccesses != DefaultHalfOpenSuccesses {
		t.Errorf("HalfOpenSuccesses = %d, want %d", cfg.HalfOpenSuccesses, DefaultHalfOpenSuccesses)
	}
	if cfg.FailureWindow != DefaultFailureWindow {
		t.Errorf("FailureWindow = %v, want %v", cfg.FailureWindow, DefaultFailureWindow)
	}
	if cfg.MaxBackoff != DefaultMaxBackoff {
		t.Errorf("MaxBackoff = %v, want %v", cfg.MaxBackoff, DefaultMaxBackoff)
	}
}

func TestSlidingWindowExpiry(t *testing.T) {
	cfg := Config{
		Threshold:         3,
		ResetTimeout:      time.Hour,
		MaxBackoff:        time.Hour,
		FailureWindow:     50 * time.Millisecond, // short window
		HalfOpenSuccesses: 1,
	}
	b := New(cfg)

	b.Failure()
	b.Failure()
	time.Sleep(60 * time.Millisecond) // let failures expire
	b.Failure()                       // only 1 failure in window now

	if b.State() != Closed {
		t.Errorf("state = %v, want Closed (old failures should have expired)", b.State())
	}
}

func TestExponentialBackoff(t *testing.T) {
	cfg := Config{
		Threshold:         1,
		ResetTimeout:      10 * time.Millisecond,
		MaxBackoff:        100 * time.Millisecond,
		FailureWindow:     time.Hour,
		HalfOpenSuccesses: 1,
	}
	b := New(cfg)

	// First open: should use base timeout
	b.Failure()
	if b.State() != Open {
		t.Fatal("expected open")
	}

	// Wait for base timeout, transition to half-open, then fail again
	time.Sleep(15 * time.Millisecond)
	_ = b.Allow()
	b.Failure() // second open

	// Second open should have longer backoff (~20ms)
	backoff := b.currentBackoff()
	if backoff < 15*time.Millisecond {
		t.Errorf("second backoff = %v, expected > 15ms", backoff)
	}
}
