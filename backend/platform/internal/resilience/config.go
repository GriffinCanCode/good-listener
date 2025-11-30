package resilience

import "time"

// Circuit breaker configuration constants
const (
	// Default configuration - startup-tolerant with sliding window
	DefaultThreshold         = 10               // failures within window before opening
	DefaultResetTimeout      = 5 * time.Second  // initial backoff
	DefaultMaxBackoff        = 60 * time.Second // max exponential backoff
	DefaultFailureWindow     = 30 * time.Second // sliding window for counting failures
	DefaultHalfOpenSuccesses = 2                // successes needed to close

	// Fast configuration (aggressive, for critical paths)
	FastThreshold         = 5
	FastResetTimeout      = 3 * time.Second
	FastMaxBackoff        = 30 * time.Second
	FastFailureWindow     = 10 * time.Second
	FastHalfOpenSuccesses = 1

	// Slow configuration (lenient, for less critical paths)
	SlowThreshold         = 20
	SlowResetTimeout      = 10 * time.Second
	SlowMaxBackoff        = 120 * time.Second
	SlowFailureWindow     = 60 * time.Second
	SlowHalfOpenSuccesses = 3
)

// Config holds circuit breaker settings.
type Config struct {
	Threshold         int           // failures within window before opening
	ResetTimeout      time.Duration // initial wait before half-open attempt
	MaxBackoff        time.Duration // max backoff after repeated opens
	FailureWindow     time.Duration // sliding window for failure counting
	HalfOpenSuccesses int           // successes needed to close
}

// DefaultConfig returns startup-tolerant production defaults.
func DefaultConfig() Config {
	return Config{
		Threshold:         DefaultThreshold,
		ResetTimeout:      DefaultResetTimeout,
		MaxBackoff:        DefaultMaxBackoff,
		FailureWindow:     DefaultFailureWindow,
		HalfOpenSuccesses: DefaultHalfOpenSuccesses,
	}
}

// FastConfig returns aggressive settings for critical paths.
func FastConfig() Config {
	return Config{
		Threshold:         FastThreshold,
		ResetTimeout:      FastResetTimeout,
		MaxBackoff:        FastMaxBackoff,
		FailureWindow:     FastFailureWindow,
		HalfOpenSuccesses: FastHalfOpenSuccesses,
	}
}

// SlowConfig returns lenient settings for less critical paths.
func SlowConfig() Config {
	return Config{
		Threshold:         SlowThreshold,
		ResetTimeout:      SlowResetTimeout,
		MaxBackoff:        SlowMaxBackoff,
		FailureWindow:     SlowFailureWindow,
		HalfOpenSuccesses: SlowHalfOpenSuccesses,
	}
}

func (c Config) withDefaults() Config {
	if c.Threshold <= 0 {
		c.Threshold = DefaultThreshold
	}
	if c.ResetTimeout <= 0 {
		c.ResetTimeout = DefaultResetTimeout
	}
	if c.MaxBackoff <= 0 {
		c.MaxBackoff = DefaultMaxBackoff
	}
	if c.FailureWindow <= 0 {
		c.FailureWindow = DefaultFailureWindow
	}
	if c.HalfOpenSuccesses <= 0 {
		c.HalfOpenSuccesses = DefaultHalfOpenSuccesses
	}
	return c
}
