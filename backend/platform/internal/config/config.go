// Package config handles platform configuration with shared schema validation.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// PlatformConfig holds Go platform-specific settings.
type PlatformConfig struct {
	HTTPAddr      string
	InferenceAddr string
}

// AudioConfig holds audio capture/processing settings.
type AudioConfig struct {
	SampleRate         int
	VADThreshold       float64
	MaxSilenceChunks   int
	CaptureSystemAudio bool
	ExcludedDevices    []string
}

// ScreenConfig holds screen capture settings.
type ScreenConfig struct {
	CaptureRate              float64 // Hz
	StableCountThreshold     int
	MinTextLength            int
	PHashSimilarityThreshold float64
}

// AutoAnswerConfig holds auto-answer feature settings.
type AutoAnswerConfig struct {
	Enabled         bool
	CooldownSeconds float64
	MinQuestionLen  int
}

// MemoryConfig holds vector memory batcher settings.
type MemoryConfig struct {
	BatchMaxSize      int
	BatchFlushDelayMs int
}

// LoggingConfig holds logging settings.
type LoggingConfig struct {
	Level  string
	Format string
}

// Config is the root configuration container.
type Config struct {
	Platform   PlatformConfig
	Audio      AudioConfig
	Screen     ScreenConfig
	AutoAnswer AutoAnswerConfig
	Memory     MemoryConfig
	Logging    LoggingConfig
}

// Validate checks config against schema constraints.
func (c *Config) Validate() error {
	var errs []string
	// Audio validation
	validRates := map[int]bool{8000: true, 16000: true, 22050: true, 44100: true, 48000: true}
	if !validRates[c.Audio.SampleRate] {
		errs = append(errs, fmt.Sprintf("audio.sample_rate must be one of [8000, 16000, 22050, 44100, 48000], got %d", c.Audio.SampleRate))
	}
	if c.Audio.VADThreshold < 0 || c.Audio.VADThreshold > 1 {
		errs = append(errs, fmt.Sprintf("audio.vad_threshold must be 0-1, got %f", c.Audio.VADThreshold))
	}
	if c.Audio.MaxSilenceChunks < 1 {
		errs = append(errs, fmt.Sprintf("audio.max_silence_chunks must be >= 1, got %d", c.Audio.MaxSilenceChunks))
	}
	// Screen validation
	if c.Screen.CaptureRate < 0.1 || c.Screen.CaptureRate > 10 {
		errs = append(errs, fmt.Sprintf("screen.capture_rate must be 0.1-10, got %f", c.Screen.CaptureRate))
	}
	if c.Screen.PHashSimilarityThreshold < 0 || c.Screen.PHashSimilarityThreshold > 1 {
		errs = append(errs, fmt.Sprintf("screen.phash_similarity_threshold must be 0-1, got %f", c.Screen.PHashSimilarityThreshold))
	}
	// Memory validation
	if c.Memory.BatchMaxSize < 1 {
		errs = append(errs, fmt.Sprintf("memory.batch_max_size must be >= 1, got %d", c.Memory.BatchMaxSize))
	}
	// AutoAnswer validation
	if c.AutoAnswer.CooldownSeconds < 0 {
		errs = append(errs, fmt.Sprintf("auto_answer.cooldown_seconds must be >= 0, got %f", c.AutoAnswer.CooldownSeconds))
	}
	if c.AutoAnswer.MinQuestionLen < 1 {
		errs = append(errs, fmt.Sprintf("auto_answer.min_question_length must be >= 1, got %d", c.AutoAnswer.MinQuestionLen))
	}
	if len(errs) > 0 {
		return fmt.Errorf("config validation failed:\n  - %s", strings.Join(errs, "\n  - "))
	}
	return nil
}

// Load reads configuration from environment variables and validates.
func Load() (*Config, error) {
	cfg := &Config{
		Platform: PlatformConfig{
			HTTPAddr:      getEnv("HTTP_ADDR", ":8000"),
			InferenceAddr: getEnv("INFERENCE_ADDR", "localhost:50051"),
		},
		Audio: AudioConfig{
			SampleRate:         getEnvInt("SAMPLE_RATE", 16000),
			VADThreshold:       getEnvFloat("VAD_THRESHOLD", 0.5),
			MaxSilenceChunks:   getEnvInt("MAX_SILENCE_CHUNKS", 15),
			CaptureSystemAudio: getEnvBool("CAPTURE_SYSTEM_AUDIO", true),
			ExcludedDevices:    getEnvList("EXCLUDED_AUDIO_DEVICES", []string{"iphone", "teams"}),
		},
		Screen: ScreenConfig{
			CaptureRate:              getEnvFloat("SCREEN_CAPTURE_RATE", 1.0),
			StableCountThreshold:     getEnvInt("SCREEN_STABLE_COUNT_THRESHOLD", 2),
			MinTextLength:            getEnvInt("SCREEN_MIN_TEXT_LENGTH", 10),
			PHashSimilarityThreshold: getEnvFloat("SCREEN_PHASH_THRESHOLD", 0.95),
		},
		AutoAnswer: AutoAnswerConfig{
			Enabled:         getEnvBool("AUTO_ANSWER_ENABLED", true),
			CooldownSeconds: getEnvFloat("AUTO_ANSWER_COOLDOWN", 10.0),
			MinQuestionLen:  getEnvInt("MIN_QUESTION_LENGTH", 10),
		},
		Memory: MemoryConfig{
			BatchMaxSize:      getEnvInt("MEMORY_BATCH_MAX_SIZE", 50),
			BatchFlushDelayMs: getEnvInt("MEMORY_BATCH_FLUSH_DELAY_MS", 2000),
		},
		Logging: LoggingConfig{
			Level:  strings.ToUpper(getEnv("LOG_LEVEL", "INFO")),
			Format: strings.ToLower(getEnv("LOG_FORMAT", "text")),
		},
	}
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	return cfg, nil
}

// MustLoad calls Load and panics on error.
func MustLoad() *Config {
	cfg, err := Load()
	if err != nil {
		panic(err)
	}
	return cfg
}

func getEnv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func getEnvInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return def
}

func getEnvFloat(key string, def float64) float64 {
	if v := os.Getenv(key); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			return f
		}
	}
	return def
}

func getEnvBool(key string, def bool) bool {
	if v := os.Getenv(key); v != "" {
		return v == "true" || v == "1"
	}
	return def
}

func getEnvList(key string, def []string) []string {
	if v := os.Getenv(key); v != "" {
		parts := strings.Split(v, ",")
		result := make([]string, 0, len(parts))
		for _, p := range parts {
			if t := strings.TrimSpace(p); t != "" {
				result = append(result, t)
			}
		}
		return result
	}
	return def
}
