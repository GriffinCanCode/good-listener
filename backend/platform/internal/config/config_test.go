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
		"AUTO_ANSWER_ENABLED", "AUTO_ANSWER_COOLDOWN", "SCREEN_STABLE_COUNT_THRESHOLD",
		"SCREEN_MIN_TEXT_LENGTH", "SCREEN_PHASH_THRESHOLD", "MIN_QUESTION_LENGTH",
		"MEMORY_BATCH_MAX_SIZE", "MEMORY_BATCH_FLUSH_DELAY_MS", "LOG_LEVEL", "LOG_FORMAT",
	}
	for _, v := range envVars {
		os.Unsetenv(v)
	}

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	// Check platform defaults
	if cfg.Platform.HTTPAddr != ":8000" {
		t.Errorf("Platform.HTTPAddr = %q, want %q", cfg.Platform.HTTPAddr, ":8000")
	}
	if cfg.Platform.InferenceAddr != "localhost:50051" {
		t.Errorf("Platform.InferenceAddr = %q, want %q", cfg.Platform.InferenceAddr, "localhost:50051")
	}

	// Check audio defaults
	if cfg.Audio.SampleRate != 16000 {
		t.Errorf("Audio.SampleRate = %d, want %d", cfg.Audio.SampleRate, 16000)
	}
	if cfg.Audio.VADThreshold != 0.5 {
		t.Errorf("Audio.VADThreshold = %f, want %f", cfg.Audio.VADThreshold, 0.5)
	}
	if cfg.Audio.MaxSilenceChunks != 15 {
		t.Errorf("Audio.MaxSilenceChunks = %d, want %d", cfg.Audio.MaxSilenceChunks, 15)
	}
	if !cfg.Audio.CaptureSystemAudio {
		t.Error("Audio.CaptureSystemAudio should default to true")
	}

	// Check screen defaults
	if cfg.Screen.CaptureRate != 1.0 {
		t.Errorf("Screen.CaptureRate = %f, want %f", cfg.Screen.CaptureRate, 1.0)
	}
	if cfg.Screen.StableCountThreshold != 2 {
		t.Errorf("Screen.StableCountThreshold = %d, want %d", cfg.Screen.StableCountThreshold, 2)
	}
	if cfg.Screen.PHashSimilarityThreshold != 0.95 {
		t.Errorf("Screen.PHashSimilarityThreshold = %f, want %f", cfg.Screen.PHashSimilarityThreshold, 0.95)
	}

	// Check auto-answer defaults
	if !cfg.AutoAnswer.Enabled {
		t.Error("AutoAnswer.Enabled should default to true")
	}
	if cfg.AutoAnswer.CooldownSeconds != 10.0 {
		t.Errorf("AutoAnswer.CooldownSeconds = %f, want %f", cfg.AutoAnswer.CooldownSeconds, 10.0)
	}
	if cfg.AutoAnswer.MinQuestionLength != 10 {
		t.Errorf("AutoAnswer.MinQuestionLength = %d, want %d", cfg.AutoAnswer.MinQuestionLength, 10)
	}

	// Check memory defaults
	if cfg.Memory.QueryDefaultResults != 5 {
		t.Errorf("Memory.QueryDefaultResults = %d, want %d", cfg.Memory.QueryDefaultResults, 5)
	}
	if cfg.Memory.PruneThreshold != 10000 {
		t.Errorf("Memory.PruneThreshold = %d, want %d", cfg.Memory.PruneThreshold, 10000)
	}
	if cfg.Memory.PruneKeep != 5000 {
		t.Errorf("Memory.PruneKeep = %d, want %d", cfg.Memory.PruneKeep, 5000)
	}
	if cfg.Memory.BatchMaxSize != 50 {
		t.Errorf("Memory.BatchMaxSize = %d, want %d", cfg.Memory.BatchMaxSize, 50)
	}
	if cfg.Memory.BatchFlushDelayMs != 2000 {
		t.Errorf("Memory.BatchFlushDelayMs = %d, want %d", cfg.Memory.BatchFlushDelayMs, 2000)
	}

	// Check logging defaults
	if cfg.Logging.Level != "INFO" {
		t.Errorf("Logging.Level = %q, want %q", cfg.Logging.Level, "INFO")
	}
	if cfg.Logging.Format != "text" {
		t.Errorf("Logging.Format = %q, want %q", cfg.Logging.Format, "text")
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
	os.Setenv("LOG_LEVEL", "debug")
	os.Setenv("LOG_FORMAT", "json")
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
		os.Unsetenv("LOG_LEVEL")
		os.Unsetenv("LOG_FORMAT")
	}()

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	if cfg.Platform.HTTPAddr != ":9000" {
		t.Errorf("Platform.HTTPAddr = %q, want %q", cfg.Platform.HTTPAddr, ":9000")
	}
	if cfg.Platform.InferenceAddr != "inference:50051" {
		t.Errorf("Platform.InferenceAddr = %q, want %q", cfg.Platform.InferenceAddr, "inference:50051")
	}
	if cfg.Audio.SampleRate != 48000 {
		t.Errorf("Audio.SampleRate = %d, want %d", cfg.Audio.SampleRate, 48000)
	}
	if cfg.Audio.VADThreshold != 0.7 {
		t.Errorf("Audio.VADThreshold = %f, want %f", cfg.Audio.VADThreshold, 0.7)
	}
	if cfg.Audio.MaxSilenceChunks != 20 {
		t.Errorf("Audio.MaxSilenceChunks = %d, want %d", cfg.Audio.MaxSilenceChunks, 20)
	}
	if cfg.Audio.CaptureSystemAudio {
		t.Error("Audio.CaptureSystemAudio should be false")
	}
	if cfg.Screen.CaptureRate != 2.5 {
		t.Errorf("Screen.CaptureRate = %f, want %f", cfg.Screen.CaptureRate, 2.5)
	}
	if cfg.AutoAnswer.Enabled {
		t.Error("AutoAnswer.Enabled should be false")
	}
	if cfg.AutoAnswer.CooldownSeconds != 15.0 {
		t.Errorf("AutoAnswer.CooldownSeconds = %f, want %f", cfg.AutoAnswer.CooldownSeconds, 15.0)
	}
	if cfg.Logging.Level != "DEBUG" {
		t.Errorf("Logging.Level = %q, want %q", cfg.Logging.Level, "DEBUG")
	}
	if cfg.Logging.Format != "json" {
		t.Errorf("Logging.Format = %q, want %q", cfg.Logging.Format, "json")
	}
}

func TestValidation(t *testing.T) {
	// Test invalid sample rate
	os.Setenv("SAMPLE_RATE", "12345")
	defer os.Unsetenv("SAMPLE_RATE")

	_, err := Load()
	if err == nil {
		t.Error("Load() should fail with invalid sample rate")
	}
}

func TestValidationVADThreshold(t *testing.T) {
	os.Setenv("VAD_THRESHOLD", "1.5")
	defer os.Unsetenv("VAD_THRESHOLD")

	_, err := Load()
	if err == nil {
		t.Error("Load() should fail with VAD threshold > 1")
	}
}

func TestValidationScreenCaptureRate(t *testing.T) {
	os.Setenv("SCREEN_CAPTURE_RATE", "0.01")
	defer os.Unsetenv("SCREEN_CAPTURE_RATE")

	_, err := Load()
	if err == nil {
		t.Error("Load() should fail with screen capture rate < 0.1")
	}
}

func TestMustLoad(t *testing.T) {
	// Clear env to ensure defaults (which are valid)
	os.Unsetenv("SAMPLE_RATE")
	os.Unsetenv("VAD_THRESHOLD")

	// Should not panic with valid defaults
	cfg := MustLoad()
	if cfg == nil {
		t.Error("MustLoad() returned nil")
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
