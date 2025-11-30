package config

import (
	"os"
	"testing"
)

func TestLoad(t *testing.T) {
	// Clear environment
	envVars := []string{
		"HTTP_ADDR", "INFERENCE_ADDR", "SAMPLE_RATE", "VAD_THRESHOLD",
		"MAX_SILENCE_CHUNKS", "CAPTURE_SYSTEM_AUDIO", "SCREEN_CAPTURE_RATE",
		"AUTO_ANSWER_ENABLED", "AUTO_ANSWER_COOLDOWN",
	}
	for _, v := range envVars {
		os.Unsetenv(v)
	}

	cfg := Load()

	// Check defaults
	if cfg.HTTPAddr != ":8000" {
		t.Errorf("HTTPAddr = %q, want %q", cfg.HTTPAddr, ":8000")
	}
	if cfg.InferenceAddr != "localhost:50051" {
		t.Errorf("InferenceAddr = %q, want %q", cfg.InferenceAddr, "localhost:50051")
	}
	if cfg.SampleRate != 16000 {
		t.Errorf("SampleRate = %d, want %d", cfg.SampleRate, 16000)
	}
	if cfg.VADThreshold != 0.5 {
		t.Errorf("VADThreshold = %f, want %f", cfg.VADThreshold, 0.5)
	}
	if cfg.MaxSilenceChunks != 15 {
		t.Errorf("MaxSilenceChunks = %d, want %d", cfg.MaxSilenceChunks, 15)
	}
	if !cfg.CaptureSystemAudio {
		t.Error("CaptureSystemAudio should default to true")
	}
	if cfg.ScreenCaptureRate != 1.0 {
		t.Errorf("ScreenCaptureRate = %f, want %f", cfg.ScreenCaptureRate, 1.0)
	}
	if !cfg.AutoAnswerEnabled {
		t.Error("AutoAnswerEnabled should default to true")
	}
	if cfg.AutoAnswerCooldown != 10.0 {
		t.Errorf("AutoAnswerCooldown = %f, want %f", cfg.AutoAnswerCooldown, 10.0)
	}
}

func TestLoadWithEnv(t *testing.T) {
	// Set environment variables
	os.Setenv("HTTP_ADDR", ":9000")
	os.Setenv("INFERENCE_ADDR", "inference:50051")
	os.Setenv("SAMPLE_RATE", "48000")
	os.Setenv("VAD_THRESHOLD", "0.7")
	os.Setenv("MAX_SILENCE_CHUNKS", "20")
	os.Setenv("CAPTURE_SYSTEM_AUDIO", "false")
	os.Setenv("SCREEN_CAPTURE_RATE", "2.5")
	os.Setenv("AUTO_ANSWER_ENABLED", "false")
	os.Setenv("AUTO_ANSWER_COOLDOWN", "15.0")
	defer func() {
		os.Unsetenv("HTTP_ADDR")
		os.Unsetenv("INFERENCE_ADDR")
		os.Unsetenv("SAMPLE_RATE")
		os.Unsetenv("VAD_THRESHOLD")
		os.Unsetenv("MAX_SILENCE_CHUNKS")
		os.Unsetenv("CAPTURE_SYSTEM_AUDIO")
		os.Unsetenv("SCREEN_CAPTURE_RATE")
		os.Unsetenv("AUTO_ANSWER_ENABLED")
		os.Unsetenv("AUTO_ANSWER_COOLDOWN")
	}()

	cfg := Load()

	if cfg.HTTPAddr != ":9000" {
		t.Errorf("HTTPAddr = %q, want %q", cfg.HTTPAddr, ":9000")
	}
	if cfg.InferenceAddr != "inference:50051" {
		t.Errorf("InferenceAddr = %q, want %q", cfg.InferenceAddr, "inference:50051")
	}
	if cfg.SampleRate != 48000 {
		t.Errorf("SampleRate = %d, want %d", cfg.SampleRate, 48000)
	}
	if cfg.VADThreshold != 0.7 {
		t.Errorf("VADThreshold = %f, want %f", cfg.VADThreshold, 0.7)
	}
	if cfg.MaxSilenceChunks != 20 {
		t.Errorf("MaxSilenceChunks = %d, want %d", cfg.MaxSilenceChunks, 20)
	}
	if cfg.CaptureSystemAudio {
		t.Error("CaptureSystemAudio should be false")
	}
	if cfg.ScreenCaptureRate != 2.5 {
		t.Errorf("ScreenCaptureRate = %f, want %f", cfg.ScreenCaptureRate, 2.5)
	}
	if cfg.AutoAnswerEnabled {
		t.Error("AutoAnswerEnabled should be false")
	}
	if cfg.AutoAnswerCooldown != 15.0 {
		t.Errorf("AutoAnswerCooldown = %f, want %f", cfg.AutoAnswerCooldown, 15.0)
	}
}

func TestGetEnvHelpers(t *testing.T) {
	// Test getEnv
	os.Setenv("TEST_STRING", "hello")
	defer os.Unsetenv("TEST_STRING")
	if v := getEnv("TEST_STRING", "default"); v != "hello" {
		t.Errorf("getEnv = %q, want %q", v, "hello")
	}
	if v := getEnv("NONEXISTENT", "default"); v != "default" {
		t.Errorf("getEnv = %q, want %q", v, "default")
	}

	// Test getEnvInt
	os.Setenv("TEST_INT", "42")
	defer os.Unsetenv("TEST_INT")
	if v := getEnvInt("TEST_INT", 0); v != 42 {
		t.Errorf("getEnvInt = %d, want %d", v, 42)
	}
	if v := getEnvInt("NONEXISTENT", 99); v != 99 {
		t.Errorf("getEnvInt = %d, want %d", v, 99)
	}
	os.Setenv("TEST_INT_INVALID", "not-a-number")
	defer os.Unsetenv("TEST_INT_INVALID")
	if v := getEnvInt("TEST_INT_INVALID", 100); v != 100 {
		t.Errorf("getEnvInt with invalid = %d, want %d", v, 100)
	}

	// Test getEnvFloat
	os.Setenv("TEST_FLOAT", "3.14")
	defer os.Unsetenv("TEST_FLOAT")
	if v := getEnvFloat("TEST_FLOAT", 0.0); v != 3.14 {
		t.Errorf("getEnvFloat = %f, want %f", v, 3.14)
	}
	if v := getEnvFloat("NONEXISTENT", 2.71); v != 2.71 {
		t.Errorf("getEnvFloat = %f, want %f", v, 2.71)
	}

	// Test getEnvBool
	os.Setenv("TEST_BOOL_TRUE", "true")
	os.Setenv("TEST_BOOL_ONE", "1")
	os.Setenv("TEST_BOOL_FALSE", "false")
	defer func() {
		os.Unsetenv("TEST_BOOL_TRUE")
		os.Unsetenv("TEST_BOOL_ONE")
		os.Unsetenv("TEST_BOOL_FALSE")
	}()
	if !getEnvBool("TEST_BOOL_TRUE", false) {
		t.Error("getEnvBool should return true for 'true'")
	}
	if !getEnvBool("TEST_BOOL_ONE", false) {
		t.Error("getEnvBool should return true for '1'")
	}
	if getEnvBool("TEST_BOOL_FALSE", true) {
		t.Error("getEnvBool should return false for 'false'")
	}
	if !getEnvBool("NONEXISTENT", true) {
		t.Error("getEnvBool should return default true")
	}
}
