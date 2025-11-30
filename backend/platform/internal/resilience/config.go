package resilience

import "time"

// Config holds circuit breaker settings
type Config struct {
	Threshold         int           // failures before opening
	ResetTimeout      time.Duration // wait before half-open attempt
	HalfOpenSuccesses int           // successes needed to close
}

// DefaultConfig returns production-ready defaults
func DefaultConfig() Config {
	return Config{
		Threshold:         5,
		ResetTimeout:      30 * time.Second,
		HalfOpenSuccesses: 3,
	}
}

// FastConfig returns aggressive settings for critical paths
func FastConfig() Config {
	return Config{
		Threshold:         3,
		ResetTimeout:      10 * time.Second,
		HalfOpenSuccesses: 2,
	}
}

// SlowConfig returns lenient settings for less critical paths
func SlowConfig() Config {
	return Config{
		Threshold:         10,
		ResetTimeout:      60 * time.Second,
		HalfOpenSuccesses: 5,
	}
}

func (c Config) withDefaults() Config {
	if c.Threshold <= 0 {
		c.Threshold = 5
	}
	if c.ResetTimeout <= 0 {
		c.ResetTimeout = 30 * time.Second
	}
	if c.HalfOpenSuccesses <= 0 {
		c.HalfOpenSuccesses = 3
	}
	return c
}
