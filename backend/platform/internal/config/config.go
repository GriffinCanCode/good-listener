// Package config handles platform configuration
package config

import (
	"os"
	"strconv"
	"strings"
)

type Config struct {
	HTTPAddr             string
	InferenceAddr        string
	SampleRate           int
	VADThreshold         float64
	MaxSilenceChunks     int
	CaptureSystemAudio   bool
	ExcludedAudioDevices []string
	ScreenCaptureRate    float64 // Hz
	AutoAnswerEnabled    bool
	AutoAnswerCooldown   float64 // seconds
}

func Load() *Config {
	return &Config{
		HTTPAddr:             getEnv("HTTP_ADDR", ":8000"),
		InferenceAddr:        getEnv("INFERENCE_ADDR", "localhost:50051"),
		SampleRate:           getEnvInt("SAMPLE_RATE", 16000),
		VADThreshold:         getEnvFloat("VAD_THRESHOLD", 0.5),
		MaxSilenceChunks:     getEnvInt("MAX_SILENCE_CHUNKS", 15),
		CaptureSystemAudio:   getEnvBool("CAPTURE_SYSTEM_AUDIO", true),
		ExcludedAudioDevices: getEnvList("EXCLUDED_AUDIO_DEVICES", []string{"iphone", "teams"}),
		ScreenCaptureRate:    getEnvFloat("SCREEN_CAPTURE_RATE", 1.0),
		AutoAnswerEnabled:    getEnvBool("AUTO_ANSWER_ENABLED", true),
		AutoAnswerCooldown:   getEnvFloat("AUTO_ANSWER_COOLDOWN", 10.0),
	}
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
