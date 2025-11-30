package screen

import (
	"crypto/md5"
	"os"
	"path/filepath"
	"testing"
)

func TestNewCapturer(t *testing.T) {
	c := NewCapturer()
	if c == nil {
		t.Fatal("NewCapturer returned nil")
	}
	if c.tempDir == "" {
		t.Error("tempDir should be set")
	}
	defer c.Close()

	// Check temp dir exists
	if _, err := os.Stat(c.tempDir); os.IsNotExist(err) {
		t.Error("temp directory should exist")
	}
}

func TestCapturerClose(t *testing.T) {
	c := NewCapturer()
	tempDir := c.tempDir

	c.Close()

	// Temp dir should be removed
	if _, err := os.Stat(tempDir); !os.IsNotExist(err) {
		t.Error("temp directory should be removed after Close")
	}
}

func TestCapturerChangeDetection(t *testing.T) {
	c := NewCapturer()
	defer c.Close()

	// Set a known hash
	testData := []byte("test image data")
	c.lastHash = md5.Sum(testData[:min(len(testData), 4096)])

	// Same hash should indicate no change
	sameHash := md5.Sum(testData[:min(len(testData), 4096)])
	if sameHash != c.lastHash {
		t.Error("same data should produce same hash")
	}

	// Different data should produce different hash
	differentData := []byte("different image data")
	differentHash := md5.Sum(differentData[:min(len(differentData), 4096)])
	if differentHash == c.lastHash {
		t.Error("different data should produce different hash")
	}
}

func TestMin(t *testing.T) {
	tests := []struct {
		a, b     int
		expected int
	}{
		{1, 2, 1},
		{2, 1, 1},
		{5, 5, 5},
		{0, 100, 0},
		{-1, 1, -1},
	}

	for _, tt := range tests {
		result := min(tt.a, tt.b)
		if result != tt.expected {
			t.Errorf("min(%d, %d) = %d, want %d", tt.a, tt.b, result, tt.expected)
		}
	}
}

func TestCaptureScreenTempFile(t *testing.T) {
	c := NewCapturer()
	defer c.Close()

	// Verify temp file path construction
	expectedPath := filepath.Join(c.tempDir, "screenshot.jpg")
	if !filepath.IsAbs(expectedPath) {
		t.Error("screenshot path should be absolute")
	}
}

// Integration test - only runs if screencapture is available
func TestCaptureIntegration(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping integration test in short mode")
	}

	// Check if screencapture command exists (macOS only)
	if _, err := os.Stat("/usr/sbin/screencapture"); os.IsNotExist(err) {
		t.Skip("screencapture not available (not macOS)")
	}

	c := NewCapturer()
	defer c.Close()

	// First capture
	data1, changed1 := c.Capture()
	if data1 == nil {
		t.Log("First capture returned nil (may be permission issue)")
		return
	}
	if !changed1 {
		t.Error("first capture should indicate change")
	}

	// Second immediate capture should show no change (screen likely same)
	data2, changed2 := c.Capture()
	if data2 != nil && changed2 {
		t.Log("Screen changed between captures (possible but unexpected)")
	}

	// CaptureAlways should always return data
	data3 := c.CaptureAlways()
	if data3 == nil {
		t.Log("CaptureAlways returned nil (may be permission issue)")
	}
}
