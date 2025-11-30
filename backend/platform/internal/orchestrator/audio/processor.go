// Package audio handles audio processing with VAD
package audio

import (
	"context"
	"encoding/binary"
	"log/slog"
	"math"
	"sync"
	"time"

	audiocap "github.com/good-listener/platform/internal/audio"
)

// VADClient interface for speech detection
type VADClient interface {
	DetectSpeech(ctx context.Context, audio []byte, sampleRate int32) (float32, bool, error)
	ResetVAD(ctx context.Context) error
}

// SpeechHandler handles completed speech segments
type SpeechHandler func(ctx context.Context, audio []float32, source string)

// vadState tracks VAD state per device
type vadState struct {
	buffer        []float32
	speechBuffer  []float32
	isSpeaking    bool
	silenceChunks int
	lastSeen      time.Time
}

// Config for audio processor
type Config struct {
	SampleRate       int
	VADThreshold     float64
	MaxSilenceChunks int
	MinSpeechSamples int // Minimum samples for valid speech (e.g., sampleRate/2 for 0.5s)
}

// Processor handles audio chunks with VAD
type Processor struct {
	vad          VADClient
	cfg          Config
	onSpeech     SpeechHandler
	mu           sync.Mutex
	vadState     map[string]*vadState
	staleTimeout time.Duration
}

// NewProcessor creates an audio processor
func NewProcessor(vad VADClient, cfg Config, onSpeech SpeechHandler) *Processor {
	if cfg.MinSpeechSamples == 0 {
		cfg.MinSpeechSamples = cfg.SampleRate / 2
	}
	return &Processor{
		vad:          vad,
		cfg:          cfg,
		onSpeech:     onSpeech,
		vadState:     make(map[string]*vadState),
		staleTimeout: 5 * time.Minute,
	}
}

// ProcessChunk processes an audio chunk through VAD
func (p *Processor) ProcessChunk(ctx context.Context, chunk audiocap.Chunk) {
	p.mu.Lock()
	state, ok := p.vadState[chunk.DeviceID]
	if !ok {
		state = &vadState{lastSeen: time.Now()}
		p.vadState[chunk.DeviceID] = state
	} else {
		state.lastSeen = time.Now()
	}
	p.mu.Unlock()

	state.buffer = append(state.buffer, chunk.Data...)

	// Process in 512-sample VAD windows
	for len(state.buffer) >= 512 {
		vadChunk := state.buffer[:512]
		state.buffer = state.buffer[512:]

		audioBytes := Float32ToBytes(vadChunk)
		prob, isSpeech, err := p.vad.DetectSpeech(ctx, audioBytes, int32(p.cfg.SampleRate))
		if err != nil {
			slog.Debug("VAD error", "error", err)
			continue
		}

		if isSpeech || prob > float32(p.cfg.VADThreshold) {
			state.isSpeaking = true
			state.silenceChunks = 0
			state.speechBuffer = append(state.speechBuffer, vadChunk...)
		} else if state.isSpeaking {
			state.speechBuffer = append(state.speechBuffer, vadChunk...)
			state.silenceChunks++

			if state.silenceChunks > p.cfg.MaxSilenceChunks {
				state.isSpeaking = false
				if len(state.speechBuffer) > p.cfg.MinSpeechSamples {
					go p.onSpeech(ctx, state.speechBuffer, chunk.Source)
				}
				state.speechBuffer = nil
				_ = p.vad.ResetVAD(ctx)
			}
		}
	}
}

// CleanupStale removes stale VAD state entries
func (p *Processor) CleanupStale() {
	p.mu.Lock()
	defer p.mu.Unlock()

	threshold := time.Now().Add(-p.staleTimeout)
	for key, state := range p.vadState {
		if state.lastSeen.Before(threshold) {
			delete(p.vadState, key)
			slog.Debug("cleaned up stale VAD state", "device", key)
		}
	}
}

// Reset clears all VAD state
func (p *Processor) Reset() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.vadState = make(map[string]*vadState)
}

// Float32ToBytes converts float32 samples to bytes
func Float32ToBytes(samples []float32) []byte {
	buf := make([]byte, len(samples)*4)
	for i, s := range samples {
		binary.LittleEndian.PutUint32(buf[i*4:], math.Float32bits(s))
	}
	return buf
}
