// Package autoanswer handles automatic question detection and answering
package autoanswer

import (
	"context"
	"log/slog"
	"sync"
	"time"
)

// QuestionDetector interface for question detection
type QuestionDetector interface {
	IsQuestion(ctx context.Context, text string) (bool, error)
}

// Detector handles auto-answer logic
type Detector struct {
	detector QuestionDetector
	mu       sync.Mutex
	enabled  bool
	cooldown time.Duration
	lastTime time.Time
}

// NewDetector creates an auto-answer detector
func NewDetector(detector QuestionDetector, cooldownSec float64, enabled bool) *Detector {
	return &Detector{
		detector: detector,
		enabled:  enabled,
		cooldown: time.Duration(cooldownSec * float64(time.Second)),
	}
}

// Check tests if text is a question that should be auto-answered
// Returns true if auto-answer should trigger
func (d *Detector) Check(ctx context.Context, text string) bool {
	if !d.IsEnabled() {
		return false
	}

	d.mu.Lock()
	if time.Since(d.lastTime) < d.cooldown {
		d.mu.Unlock()
		return false
	}
	d.mu.Unlock()

	isQ, err := d.detector.IsQuestion(ctx, text)
	if err != nil || !isQ {
		return false
	}

	d.mu.Lock()
	d.lastTime = time.Now()
	d.mu.Unlock()

	slog.Info("auto-answering question", "question", text)
	return true
}

// SetEnabled enables/disables auto-answering
func (d *Detector) SetEnabled(enabled bool) {
	d.mu.Lock()
	d.enabled = enabled
	d.mu.Unlock()
	slog.Info("auto-answer state changed", "enabled", enabled)
}

// IsEnabled returns current enabled state
func (d *Detector) IsEnabled() bool {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.enabled
}
