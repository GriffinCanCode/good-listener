//go:build linux

package screen

import (
	"bytes"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
)

type linuxBackend struct{ tempDir string }

func (l *linuxBackend) captureRaw() []byte {
	tmpFile := filepath.Join(l.tempDir, "screenshot.jpg")
	// Try gnome-screenshot first, fall back to scrot
	var cmd *exec.Cmd
	if _, err := exec.LookPath("gnome-screenshot"); err == nil {
		cmd = exec.Command("gnome-screenshot", "-f", tmpFile)
	} else if _, err := exec.LookPath("scrot"); err == nil {
		cmd = exec.Command("scrot", "-o", tmpFile)
	} else {
		slog.Error("no screenshot tool found (install gnome-screenshot or scrot)")
		return nil
	}
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		slog.Error("screenshot failed", "error", err, "stderr", stderr.String())
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

func (l *linuxBackend) cleanup() {}

// New creates a platform-specific screen capturer
func New() Capturer {
	tmpDir, err := os.MkdirTemp("", "goodlistener-screen-*")
	if err != nil {
		slog.Error("failed to create temp dir", "error", err)
		tmpDir = os.TempDir()
	}
	return newBase(&linuxBackend{tempDir: tmpDir}, tmpDir)
}
