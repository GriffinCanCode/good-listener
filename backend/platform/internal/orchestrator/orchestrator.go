// Package orchestrator coordinates audio, screen, and inference services
package orchestrator

import (
	"context"
	"encoding/binary"
	"log/slog"
	"math"
	"strings"
	"sync"
	"time"

	"github.com/good-listener/platform/internal/audio"
	"github.com/good-listener/platform/internal/config"
	"github.com/good-listener/platform/internal/grpcclient"
	"github.com/good-listener/platform/internal/screen"
	pb "github.com/good-listener/platform/pkg/pb"
)

// TranscriptEvent represents a transcription event
type TranscriptEvent struct {
	Text   string
	Source string
}

// Orchestrator coordinates all services
type Orchestrator struct {
	inference *grpcclient.Client
	cfg       *config.Config

	audioCap  *audio.Capturer
	screenCap *screen.Capturer

	// State
	mu                sync.RWMutex
	latestScreenText  string
	latestScreenImage []byte
	recentTranscripts []transcriptEntry
	recording         bool
	autoAnswer        bool

	// Channels
	transcriptCh chan TranscriptEvent
	stopCh       chan struct{}

	// VAD state per device
	vadState map[string]*vadState

	// Auto-answer cooldown
	lastAutoAnswer time.Time
}

type transcriptEntry struct {
	timestamp time.Time
	text      string
	source    string
}

type vadState struct {
	buffer        []float32
	speechBuffer  []float32
	isSpeaking    bool
	silenceChunks int
}

// New creates a new orchestrator
func New(inference *grpcclient.Client, cfg *config.Config) *Orchestrator {
	audioCap, err := audio.NewCapturer(cfg.SampleRate, 100, cfg.CaptureSystemAudio)
	if err != nil {
		slog.Error("failed to create audio capturer", "error", err)
	}

	return &Orchestrator{
		inference:    inference,
		cfg:          cfg,
		audioCap:     audioCap,
		screenCap:    screen.NewCapturer(),
		recording:    true,
		autoAnswer:   cfg.AutoAnswerEnabled,
		transcriptCh: make(chan TranscriptEvent, 100),
		stopCh:       make(chan struct{}),
		vadState:     make(map[string]*vadState),
	}
}

// TranscriptEvents returns channel for transcript events
func (o *Orchestrator) TranscriptEvents() <-chan TranscriptEvent {
	return o.transcriptCh
}

// Start begins orchestration
func (o *Orchestrator) Start(ctx context.Context) error {
	if o.audioCap != nil {
		if err := o.audioCap.Start(ctx); err != nil {
			slog.Warn("audio capture start failed", "error", err)
		}
		go o.audioLoop(ctx)
	}

	go o.screenLoop(ctx)

	return nil
}

// Stop stops orchestration
func (o *Orchestrator) Stop() {
	close(o.stopCh)
	if o.audioCap != nil {
		o.audioCap.Stop()
	}
}

func (o *Orchestrator) audioLoop(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-o.stopCh:
			return
		case chunk := <-o.audioCap.Output():
			o.processAudioChunk(ctx, chunk)
		}
	}
}

func (o *Orchestrator) processAudioChunk(ctx context.Context, chunk audio.Chunk) {
	deviceKey := chunk.DeviceID

	o.mu.Lock()
	state, ok := o.vadState[deviceKey]
	if !ok {
		state = &vadState{}
		o.vadState[deviceKey] = state
	}
	o.mu.Unlock()

	// Add to VAD buffer
	state.buffer = append(state.buffer, chunk.Data...)

	// Process in 512-sample chunks (VAD window size)
	for len(state.buffer) >= 512 {
		vadChunk := state.buffer[:512]
		state.buffer = state.buffer[512:]

		// Call VAD service
		audioBytes := float32ToBytes(vadChunk)
		prob, isSpeech, err := o.inference.DetectSpeech(ctx, audioBytes, int32(o.cfg.SampleRate))
		if err != nil {
			slog.Debug("VAD error", "error", err)
			continue
		}

		if isSpeech || prob > float32(o.cfg.VADThreshold) {
			state.isSpeaking = true
			state.silenceChunks = 0
			state.speechBuffer = append(state.speechBuffer, vadChunk...)
		} else if state.isSpeaking {
			state.speechBuffer = append(state.speechBuffer, vadChunk...)
			state.silenceChunks++

			if state.silenceChunks > o.cfg.MaxSilenceChunks {
				state.isSpeaking = false

				// Transcribe if we have enough audio (> 0.5 sec)
				if len(state.speechBuffer) > o.cfg.SampleRate/2 {
					go o.transcribe(ctx, state.speechBuffer, chunk.Source)
				}

				state.speechBuffer = nil
				_ = o.inference.ResetVAD(ctx)
			}
		}
	}
}

func (o *Orchestrator) transcribe(ctx context.Context, audio []float32, source string) {
	audioBytes := float32ToBytes(audio)
	text, err := o.inference.Transcribe(ctx, audioBytes, int32(o.cfg.SampleRate))
	if err != nil {
		slog.Error("transcription error", "error", err)
		return
	}

	text = strings.TrimSpace(text)
	if text == "" {
		return
	}

	slog.Info("transcribed", "source", source, "text", text)

	// Store in memory
	o.mu.Lock()
	o.recentTranscripts = append(o.recentTranscripts, transcriptEntry{
		timestamp: time.Now(),
		text:      text,
		source:    source,
	})
	// Keep last 30 entries
	if len(o.recentTranscripts) > 30 {
		o.recentTranscripts = o.recentTranscripts[len(o.recentTranscripts)-30:]
	}
	o.mu.Unlock()

	// Emit transcript event
	select {
	case o.transcriptCh <- TranscriptEvent{Text: text, Source: source}:
	default:
		slog.Debug("transcript channel full")
	}

	// Store to vector DB if recording
	if o.recording && len(strings.Fields(text)) >= 4 {
		_ = o.inference.StoreMemory(ctx, source+": "+text, "audio")
	}

	// Check for auto-answer on system audio
	if o.autoAnswer && source == "system" {
		o.maybeAutoAnswer(ctx, text)
	}
}

func (o *Orchestrator) maybeAutoAnswer(ctx context.Context, text string) {
	o.mu.Lock()
	if time.Since(o.lastAutoAnswer) < time.Duration(o.cfg.AutoAnswerCooldown)*time.Second {
		o.mu.Unlock()
		return
	}
	o.mu.Unlock()

	isQuestion, err := o.inference.IsQuestion(ctx, text)
	if err != nil || !isQuestion {
		return
	}

	o.mu.Lock()
	o.lastAutoAnswer = time.Now()
	o.mu.Unlock()

	slog.Info("auto-answering question", "question", text)
	// Auto-answer handled by WebSocket handler
}

func (o *Orchestrator) screenLoop(ctx context.Context) {
	interval := time.Duration(float64(time.Second) / o.cfg.ScreenCaptureRate)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	var lastStoredText string
	stableCount := 0

	for {
		select {
		case <-ctx.Done():
			return
		case <-o.stopCh:
			return
		case <-ticker.C:
			imgData, changed := o.screenCap.Capture()
			if !changed || imgData == nil {
				continue
			}

			o.mu.Lock()
			o.latestScreenImage = imgData
			o.mu.Unlock()

			// OCR
			text, err := o.inference.ExtractText(ctx, imgData, "jpeg")
			if err != nil {
				slog.Debug("OCR error", "error", err)
				continue
			}

			o.mu.Lock()
			if text != o.latestScreenText {
				o.latestScreenText = text
				stableCount = 0
			} else {
				stableCount++
			}

			// Store stable screen text to memory
			if o.recording && stableCount >= 2 && text != lastStoredText && len(text) > 50 {
				go func(t string) {
					_ = o.inference.StoreMemory(ctx, t, "screen")
				}(text)
				lastStoredText = text
				stableCount = 0
			}
			o.mu.Unlock()
		}
	}
}

// GetRecentTranscript returns transcript from last N seconds
func (o *Orchestrator) GetRecentTranscript(seconds int) string {
	o.mu.RLock()
	defer o.mu.RUnlock()

	cutoff := time.Now().Add(-time.Duration(seconds) * time.Second)
	var parts []string
	for _, e := range o.recentTranscripts {
		if e.timestamp.After(cutoff) {
			parts = append(parts, strings.ToUpper(e.source)+": "+e.text)
		}
	}
	return strings.Join(parts, "\n")
}

// GetLatestScreenText returns the latest OCR text
func (o *Orchestrator) GetLatestScreenText() string {
	o.mu.RLock()
	defer o.mu.RUnlock()
	return o.latestScreenText
}

// GetLatestScreenImage returns the latest screenshot
func (o *Orchestrator) GetLatestScreenImage() []byte {
	o.mu.RLock()
	defer o.mu.RUnlock()
	return o.latestScreenImage
}

// SetRecording enables/disables memory recording
func (o *Orchestrator) SetRecording(enabled bool) {
	o.mu.Lock()
	o.recording = enabled
	o.mu.Unlock()
	slog.Info("recording state changed", "enabled", enabled)
}

// SetAutoAnswer enables/disables auto-answering
func (o *Orchestrator) SetAutoAnswer(enabled bool) {
	o.mu.Lock()
	o.autoAnswer = enabled
	o.mu.Unlock()
	slog.Info("auto-answer state changed", "enabled", enabled)
}

// Analyze sends a query to the LLM
func (o *Orchestrator) Analyze(ctx context.Context, query string, onChunk func(string)) error {
	transcript := o.GetRecentTranscript(300)
	screenText := o.GetLatestScreenText()

	req := &pb.AnalyzeRequest{
		UserQuery:   query,
		Transcript:  transcript,
		ContextText: screenText,
		ImageData:   o.GetLatestScreenImage(),
	}

	return o.inference.AnalyzeStream(ctx, req, onChunk)
}

func float32ToBytes(samples []float32) []byte {
	buf := make([]byte, len(samples)*4)
	for i, s := range samples {
		bits := math.Float32bits(s)
		binary.LittleEndian.PutUint32(buf[i*4:], bits)
	}
	return buf
}
