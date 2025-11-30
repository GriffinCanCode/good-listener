// Package screen provides platform-agnostic screen capture
package screen

import (
	"crypto/md5"
	"os"
)

// Capturer captures screenshots with change detection
type Capturer interface {
	Capture() ([]byte, bool)
	CaptureAlways() []byte
	Close()
}

// backend implements platform-specific raw capture
type backend interface {
	captureRaw() []byte
	cleanup()
}

// baseCapturer provides shared hash-based change detection
type baseCapturer struct {
	backend
	lastHash [16]byte
	tempDir  string
}

func newBase(b backend, tempDir string) *baseCapturer {
	return &baseCapturer{backend: b, tempDir: tempDir}
}

func (c *baseCapturer) Capture() ([]byte, bool) {
	data := c.captureRaw()
	if data == nil {
		return nil, false
	}
	hash := md5.Sum(data[:min(len(data), 4096)])
	if hash == c.lastHash {
		return nil, false
	}
	c.lastHash = hash
	return data, true
}

func (c *baseCapturer) CaptureAlways() []byte {
	data := c.captureRaw()
	if data != nil {
		c.lastHash = md5.Sum(data[:min(len(data), 4096)])
	}
	return data
}

func (c *baseCapturer) Close() {
	c.cleanup()
	if c.tempDir != "" {
		os.RemoveAll(c.tempDir)
	}
}
