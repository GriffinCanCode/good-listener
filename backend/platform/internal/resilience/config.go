package resilience

import "time"

// Circuit breaker configuration constants
const (
	// Default configuration
	DefaultThreshold         = 5
	DefaultResetTimeout      = 30 * time.Second
	DefaultHalfOpenSuccesses = 3

	// Fast configuration (aggressive, for critical paths)
	FastThreshold         = 3
	FastResetTimeout      = 10 * time.Second
	FastHalfOpenSuccesses = 2

	// Slow configuration (lenient, for less critical paths)
	SlowThreshold         = 10
	SlowResetTimeout      = 60 * time.Second
	SlowHalfOpenSuccesses = 5
)

// Config holds circuit breaker settings.
type Config struct {
	Threshold         int           // failures before opening
	ResetTimeout      time.Duration // wait before half-open attempt
	HalfOpenSuccesses int           // successes needed to close
}

// DefaultConfig returns production-ready defaults.
func DefaultConfig() Config {
	return Config{
		Threshold:         DefaultThreshold,
		ResetTimeout:      DefaultResetTimeout,
		HalfOpenSuccesses: DefaultHalfOpenSuccesses,
	}
}

// FastConfig returns aggressive settings for critical paths.
func FastConfig() Config {
	return Config{
		Threshold:         FastThreshold,
		ResetTimeout:      FastResetTimeout,
		HalfOpenSuccesses: FastHalfOpenSuccesses,
	}
}

// SlowConfig returns lenient settings for less critical paths.
func SlowConfig() Config {
	return Config{
		Threshold:         SlowThreshold,
		ResetTimeout:      SlowResetTimeout,
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
	if c.HalfOpenSuccesses <= 0 {
		c.HalfOpenSuccesses = DefaultHalfOpenSuccesses
	}
	return c
}
