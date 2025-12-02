package audio

import (
	"context"
	"encoding/binary"
	"math"
	"testing"

	audiocap "github.com/GriffinCanCode/good-listener/backend/platform/internal/audio"
)

type mockVAD struct {
	prob    float32
	speech  bool
	resetCt int
}

func (m *mockVAD) DetectSpeech(_ context.Context, _ []byte, _ int32) (float32, bool, error) {
	return m.prob, m.speech, nil
}

func (m *mockVAD) ResetVAD(_ context.Context) error {
	m.resetCt++
	return nil
}

func TestFloat32ToBytes(t *testing.T) {
	samples := []float32{0.0, 1.0, -1.0, 0.5}
	bytes := Float32ToBytes(samples)

	if len(bytes) != len(samples)*4 {
		t.Errorf("byte length = %d, want %d", len(bytes), len(samples)*4)
	}

	// Verify first sample (0.0)
	bits := binary.LittleEndian.Uint32(bytes[0:4])
	if math.Float32frombits(bits) != 0.0 {
		t.Error("first sample should be 0.0")
	}

	// Verify second sample (1.0)
	bits = binary.LittleEndian.Uint32(bytes[4:8])
	if math.Float32frombits(bits) != 1.0 {
		t.Error("second sample should be 1.0")
	}
}

func TestProcessorCreation(t *testing.T) {
	vad := &mockVAD{}
	cfg := Config{SampleRate: 16000, VADThreshold: 0.5, MaxSilenceChunks: 15}
	called := false
	p := NewProcessor(vad, cfg, func(_ context.Context, _ []float32, _ string) { called = true }, func(_ float32, _ bool, _ string) {})

	if p == nil {
		t.Fatal("expected processor, got nil")
	}
	if p.cfg.MinSpeechSamples != 8000 {
		t.Errorf("MinSpeechSamples = %d, want 8000", p.cfg.MinSpeechSamples)
	}
	if called {
		t.Error("handler should not be called yet")
	}
}

func TestProcessorReset(t *testing.T) {
	vad := &mockVAD{}
	cfg := Config{SampleRate: 16000, VADThreshold: 0.5, MaxSilenceChunks: 15}
	p := NewProcessor(vad, cfg, func(_ context.Context, _ []float32, _ string) {}, func(_ float32, _ bool, _ string) {})

	// Add some state
	p.mu.Lock()
	p.vadState["test"] = &vadState{}
	p.mu.Unlock()

	p.Reset()

	p.mu.Lock()
	if len(p.vadState) != 0 {
		t.Error("vadState should be empty after reset")
	}
	p.mu.Unlock()
}

func TestProcessChunkCreatesState(t *testing.T) {
	vad := &mockVAD{}
	cfg := Config{SampleRate: 16000, VADThreshold: 0.5, MaxSilenceChunks: 15}
	p := NewProcessor(vad, cfg, func(_ context.Context, _ []float32, _ string) {}, func(_ float32, _ bool, _ string) {})

	chunk := audiocap.Chunk{
		Data:     make([]float32, 100),
		DeviceID: "test-device",
		Source:   "user",
	}

	p.ProcessChunk(context.Background(), chunk)

	p.mu.Lock()
	if _, ok := p.vadState["test-device"]; !ok {
		t.Error("VAD state should be created for device")
	}
	p.mu.Unlock()
}
