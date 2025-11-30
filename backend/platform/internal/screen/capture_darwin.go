//go:build darwin

package screen

import (
	"bytes"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
)

type darwinBackend struct{ tempDir string }

func (d *darwinBackend) captureRaw() []byte {
	tmpFile := filepath.Join(d.tempDir, "screenshot.jpg")
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
	os.Remove(tmpFile)
	return data
}

func (d *darwinBackend) cleanup() {}

// New creates a platform-specific screen capturer
func New() Capturer {
	tmpDir, err := os.MkdirTemp("", "goodlistener-screen-*")
	if err != nil {
		slog.Error("failed to create temp dir", "error", err)
		tmpDir = os.TempDir()
	}
	return newBase(&darwinBackend{tempDir: tmpDir}, tmpDir)
}
