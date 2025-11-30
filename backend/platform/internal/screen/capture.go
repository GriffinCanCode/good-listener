// Package screen handles screen capture using native macOS screencapture
package screen

import (
	"bytes"
	"crypto/md5"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
)

// Capturer captures screenshots using native macOS screencapture command
type Capturer struct {
	lastHash [16]byte
	tempDir  string
}

// NewCapturer creates a new screen capturer
func NewCapturer() *Capturer {
	tmpDir, err := os.MkdirTemp("", "goodlistener-screen-*")
	if err != nil {
		slog.Error("failed to create temp dir for screenshots", "error", err)
		tmpDir = os.TempDir()
	}
	return &Capturer{tempDir: tmpDir}
}

// Capture captures the primary display and returns JPEG bytes
// Returns nil if screen hasn't changed significantly
func (c *Capturer) Capture() ([]byte, bool) {
	imgData := c.captureScreen()
	if imgData == nil {
		return nil, false
	}

	// Quick change detection using hash
	hash := md5.Sum(imgData[:min(len(imgData), 4096)]) // Hash first 4KB for speed
	if hash == c.lastHash {
		return nil, false
	}
	c.lastHash = hash

	return imgData, true
}

// CaptureAlways captures regardless of change detection
func (c *Capturer) CaptureAlways() []byte {
	imgData := c.captureScreen()
	if imgData != nil {
		c.lastHash = md5.Sum(imgData[:min(len(imgData), 4096)])
	}
	return imgData
}

func (c *Capturer) captureScreen() []byte {
	tmpFile := filepath.Join(c.tempDir, "screenshot.jpg")

	// Use macOS native screencapture command
	// -x: no sound, -t jpg: JPEG format, -m: main display only
	cmd := exec.Command("screencapture", "-x", "-t", "jpg", "-m", tmpFile)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		slog.Error("screencapture failed", "error", err, "stderr", stderr.String())
		return nil
	}

	data, err := os.ReadFile(tmpFile)
	if err != nil {
		slog.Error("failed to read screenshot", "error", err)
		return nil
	}

	// Clean up temp file
	os.Remove(tmpFile)

	return data
}

// Close cleans up temp directory
func (c *Capturer) Close() {
	if c.tempDir != "" {
		os.RemoveAll(c.tempDir)
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
