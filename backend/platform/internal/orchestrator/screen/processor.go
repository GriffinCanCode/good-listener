// Package screen handles screen capture and OCR processing
package screen

import (
	"bytes"
	"context"
	"image"
	_ "image/jpeg" // JPEG decoder
	_ "image/png"  // PNG decoder
	"log/slog"
	"sync"
	"time"

	screencap "github.com/GriffinCanCode/good-listener/backend/platform/internal/screen"
	"github.com/corona10/goimagehash"
)

// OCRClient interface for text extraction.
type OCRClient interface {
	ExtractText(ctx context.Context, imageData []byte, format string) (string, error)
}

// MemoryClient interface for storing screen content.
type MemoryClient interface {
	StoreMemory(ctx context.Context, text, source string) error
}

// Processor handles screen capture and OCR.
type Processor struct {
	capturer  screencap.Capturer
	ocr       OCRClient
	memory    MemoryClient
	mu        sync.RWMutex
	text      string
	image     []byte
	recording bool
	lastHash  *goimagehash.ImageHash
}

// NewProcessor creates a screen processor.
func NewProcessor(capturer screencap.Capturer, ocr OCRClient, memory MemoryClient) *Processor {
	return &Processor{
		capturer:  capturer,
		ocr:       ocr,
		memory:    memory,
		recording: true,
	}
}

// Run starts the screen capture loop.
func (p *Processor) Run(ctx context.Context, captureRate float64, stopCh <-chan struct{}) {
	interval := time.Duration(float64(time.Second) / captureRate)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	var lastStoredText string
	stableCount := 0

	for {
		select {
		case <-ctx.Done():
			return
		case <-stopCh:
			return
		case <-ticker.C:
			imgData, changed := p.capturer.Capture()
			if !changed || imgData == nil {
				continue
			}

			p.mu.Lock()
			p.image = imgData
			p.mu.Unlock()

			// Skip OCR if perceptual hash similarity > 95%
			if p.shouldSkipOCR(imgData) {
				continue
			}

			text, err := p.ocr.ExtractText(ctx, imgData, "jpeg")
			if err != nil {
				slog.Debug("OCR error", "error", err)
				continue
			}

			p.mu.Lock()
			if text != p.text {
				p.text = text
				stableCount = 0
			} else {
				stableCount++
			}

			// Store stable screen text to memory
			if p.recording && stableCount >= StableCountThreshold && text != lastStoredText && len(text) > MinTextLengthForStorage {
				go func(t string) { _ = p.memory.StoreMemory(ctx, t, "screen") }(text)
				lastStoredText = text
				stableCount = 0
			}
			p.mu.Unlock()
		}
	}
}

// shouldSkipOCR computes pHash and returns true if similarity to previous frame > 95%.
func (p *Processor) shouldSkipOCR(imgData []byte) bool {
	img, _, err := image.Decode(bytes.NewReader(imgData))
	if err != nil {
		return false
	}

	hash, err := goimagehash.PerceptionHash(img)
	if err != nil {
		return false
	}

	p.mu.Lock()
	defer p.mu.Unlock()

	if p.lastHash == nil {
		p.lastHash = hash
		return false
	}

	dist, err := p.lastHash.Distance(hash)
	if err != nil {
		p.lastHash = hash
		return false
	}

	// Skip OCR if Hamming distance <= threshold (frames are similar)
	if dist <= MaxHashDistance {
		slog.Debug("skipping OCR due to similar frame", "distance", dist)
		return true
	}

	p.lastHash = hash
	return false
}

// Text returns latest OCR text.
func (p *Processor) Text() string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.text
}

// Image returns latest screenshot.
func (p *Processor) Image() []byte {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.image
}

// SetRecording enables/disables memory recording.
func (p *Processor) SetRecording(enabled bool) {
	p.mu.Lock()
	p.recording = enabled
	p.mu.Unlock()
}
