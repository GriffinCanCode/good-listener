//go:build windows

package screen

import (
	"log/slog"
	"os"
)

type windowsBackend struct{ tempDir string }

func (w *windowsBackend) captureRaw() []byte {
	// TODO: Implement using Windows GDI or DXGI
	slog.Warn("Windows screen capture not yet implemented")
	return nil
}

func (w *windowsBackend) cleanup() {}

// New creates a platform-specific screen capturer
func New() Capturer {
	tmpDir, err := os.MkdirTemp("", "goodlistener-screen-*")
	if err != nil {
		slog.Error("failed to create temp dir", "error", err)
		tmpDir = os.TempDir()
	}
	return newBase(&windowsBackend{tempDir: tmpDir}, tmpDir)
}
