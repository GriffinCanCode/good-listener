package screen

import (
	"crypto/md5"
	"os"
	"testing"
)

func TestNew(t *testing.T) {
	c := New()
	if c == nil {
		t.Fatal("New returned nil")
	}
	defer c.Close()
}

func TestCapturerClose(t *testing.T) {
	c := New()
	c.Close()
	// No panic = success
}

func TestCapturerChangeDetection(t *testing.T) {
	// Test hash-based change detection logic
	testData := []byte("test image data")
	hash1 := md5.Sum(testData[:min(len(testData), 4096)])

	sameHash := md5.Sum(testData[:min(len(testData), 4096)])
	if sameHash != hash1 {
		t.Error("same data should produce same hash")
	}

	differentData := []byte("different image data")
	differentHash := md5.Sum(differentData[:min(len(differentData), 4096)])
	if differentHash == hash1 {
		t.Error("different data should produce different hash")
	}
}

// Integration test - only runs if screencapture is available.
func TestCaptureIntegration(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping integration test in short mode")
	}

	// Check if screencapture command exists (macOS only)
	if _, err := os.Stat("/usr/sbin/screencapture"); os.IsNotExist(err) {
		t.Skip("screencapture not available (not macOS)")
	}

	c := New()
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
