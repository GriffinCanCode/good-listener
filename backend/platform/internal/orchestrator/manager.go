// Package orchestrator coordinates audio, screen, and inference services
package orchestrator

import (
	"context"
	"strings"
	"sync"
	"time"

	audiocap "github.com/good-listener/platform/internal/audio"
	"github.com/good-listener/platform/internal/config"
	"github.com/good-listener/platform/internal/grpcclient"
	"github.com/good-listener/platform/internal/orchestrator/audio"
	"github.com/good-listener/platform/internal/orchestrator/autoanswer"
	"github.com/good-listener/platform/internal/orchestrator/screen"
	"github.com/good-listener/platform/internal/orchestrator/transcript"
	screencap "github.com/good-listener/platform/internal/screen"
	"github.com/good-listener/platform/internal/trace"
	pb "github.com/good-listener/platform/pkg/pb"
)

// TranscriptEvent re-exported for API compatibility
type TranscriptEvent = transcript.Event

// AutoAnswerEvent represents an auto-answer streaming event
type AutoAnswerEvent struct {
	Type     string // "start", "chunk", "done"
	Question string // Only for "start"
	Content  string // Only for "chunk"
}

// Orchestrator is an alias for Manager (backwards compatibility)
type Orchestrator = Manager

// Manager coordinates all services
type Manager struct {
	inference *grpcclient.Client
	cfg       *config.Config

	audioCap       *audiocap.Capturer
	audioProc      *audio.Processor
	screenProc     *screen.Processor
	transcripts    *transcript.MemoryStore
	autoAnswer     *autoanswer.Detector
	autoAnswerChan chan AutoAnswerEvent

	mu        sync.RWMutex
	recording bool
	stopCh    chan struct{}
}

// New creates a new manager
func New(inference *grpcclient.Client, cfg *config.Config) *Manager {
	log := trace.Logger(context.Background())
	audioCap, err := audiocap.NewCapturer(cfg.SampleRate, 100, cfg.CaptureSystemAudio)
	if err != nil {
		log.Error("failed to create audio capturer", "error", err)
	}

	transcripts := transcript.NewStore(30, 100)
	autoAnswerDet := autoanswer.NewDetector(inference, cfg.AutoAnswerCooldown, cfg.AutoAnswerEnabled)

	m := &Manager{
		inference:      inference,
		cfg:            cfg,
		audioCap:       audioCap,
		transcripts:    transcripts,
		autoAnswer:     autoAnswerDet,
		autoAnswerChan: make(chan AutoAnswerEvent, 10),
		recording:      true,
		stopCh:         make(chan struct{}),
	}

	// Create audio processor with speech handler
	if audioCap != nil {
		m.audioProc = audio.NewProcessor(inference, audio.Config{
			SampleRate:       cfg.SampleRate,
			VADThreshold:     cfg.VADThreshold,
			MaxSilenceChunks: cfg.MaxSilenceChunks,
		}, m.handleSpeech)
	}

	// Create screen processor
	m.screenProc = screen.NewProcessor(screencap.New(), inference, inference)

	return m
}

// handleSpeech processes completed speech segments
func (m *Manager) handleSpeech(ctx context.Context, samples []float32, source string) {
	ctx, span := trace.StartSpan(ctx, "handle_speech")
	defer span.End()
	span.SetAttr("source", source)
	span.SetAttr("samples", len(samples))

	log := trace.Logger(ctx)
	audioBytes := audio.Float32ToBytes(samples)
	text, err := m.inference.Transcribe(ctx, audioBytes, int32(m.cfg.SampleRate))
	if err != nil {
		span.SetAttr("error", err.Error())
		log.Error("transcription error", "error", err)
		return
	}

	text = strings.TrimSpace(text)
	if text == "" {
		return
	}

	log.Info("transcribed", "source", source, "text", text)

	m.transcripts.Add(text, source)
	m.transcripts.Emit(TranscriptEvent{Text: text, Source: source})

	// Store to vector DB if recording
	m.mu.RLock()
	shouldStore := m.recording && len(strings.Fields(text)) >= 4
	m.mu.RUnlock()

	if shouldStore {
		_ = m.inference.StoreMemory(ctx, source+": "+text, "audio")
	}

	// Check for auto-answer on system audio
	if source == "system" && m.autoAnswer.Check(ctx, text) {
		go m.streamAutoAnswer(ctx, text)
	}
}

// TranscriptEvents returns channel for transcript events
func (m *Manager) TranscriptEvents() <-chan TranscriptEvent {
	return m.transcripts.Events()
}

// AutoAnswerEvents returns channel for auto-answer events
func (m *Manager) AutoAnswerEvents() <-chan AutoAnswerEvent {
	return m.autoAnswerChan
}

// streamAutoAnswer generates and streams an LLM response for a detected question
func (m *Manager) streamAutoAnswer(ctx context.Context, question string) {
	ctx, span := trace.StartSpan(ctx, "stream_auto_answer")
	defer span.End()
	span.SetAttr("question", question)

	log := trace.Logger(ctx)
	log.Info("auto-answering question", "question", question)

	// Emit start event
	m.autoAnswerChan <- AutoAnswerEvent{Type: "start", Question: question}

	req := &pb.AnalyzeRequest{
		UserQuery:   "Answer this question concisely: " + question,
		Transcript:  m.GetRecentTranscript(120),
		ContextText: m.GetLatestScreenText(),
	}

	err := m.inference.AnalyzeStream(ctx, req, func(chunk string) {
		m.autoAnswerChan <- AutoAnswerEvent{Type: "chunk", Content: chunk}
	})

	if err != nil {
		span.SetAttr("error", err.Error())
		log.Error("auto-answer error", "error", err)
		m.autoAnswerChan <- AutoAnswerEvent{Type: "chunk", Content: "Error: " + err.Error()}
	}

	// Emit done event
	m.autoAnswerChan <- AutoAnswerEvent{Type: "done"}
}

// Start begins orchestration
func (m *Manager) Start(ctx context.Context) error {
	log := trace.Logger(ctx)
	if m.audioCap != nil {
		if err := m.audioCap.Start(ctx); err != nil {
			log.Warn("audio capture start failed", "error", err)
		}
		go m.audioLoop(ctx)
	}

	go m.screenProc.Run(ctx, m.cfg.ScreenCaptureRate, m.stopCh)
	go m.vadCleanupLoop(ctx)

	return nil
}

func (m *Manager) audioLoop(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-m.stopCh:
			return
		case chunk := <-m.audioCap.Output():
			m.audioProc.ProcessChunk(ctx, chunk)
		}
	}
}

func (m *Manager) vadCleanupLoop(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-m.stopCh:
			return
		case <-ticker.C:
			if m.audioProc != nil {
				m.audioProc.CleanupStale()
			}
		}
	}
}

// Stop stops orchestration
func (m *Manager) Stop() {
	close(m.stopCh)
	if m.audioCap != nil {
		m.audioCap.Stop()
	}
	if m.audioProc != nil {
		m.audioProc.Reset()
	}
}

// GetRecentTranscript returns transcript from last N seconds
func (m *Manager) GetRecentTranscript(seconds int) string {
	return m.transcripts.GetRecent(seconds)
}

// GetLatestScreenText returns the latest OCR text
func (m *Manager) GetLatestScreenText() string {
	return m.screenProc.Text()
}

// GetLatestScreenImage returns the latest screenshot
func (m *Manager) GetLatestScreenImage() []byte {
	return m.screenProc.Image()
}

// SetRecording enables/disables memory recording
func (m *Manager) SetRecording(enabled bool) {
	m.mu.Lock()
	m.recording = enabled
	m.mu.Unlock()
	m.screenProc.SetRecording(enabled)
	trace.Logger(context.Background()).Info("recording state changed", "enabled", enabled)
}

// SetAutoAnswer enables/disables auto-answering
func (m *Manager) SetAutoAnswer(enabled bool) {
	m.autoAnswer.SetEnabled(enabled)
}

// Analyze sends a query to the LLM
func (m *Manager) Analyze(ctx context.Context, query string, onChunk func(string)) error {
	ctx, span := trace.StartSpan(ctx, "orchestrator_analyze")
	defer span.End()
	span.SetAttr("query_len", len(query))

	req := &pb.AnalyzeRequest{
		UserQuery:   query,
		Transcript:  m.GetRecentTranscript(300),
		ContextText: m.GetLatestScreenText(),
		ImageData:   m.GetLatestScreenImage(),
	}
	return m.inference.AnalyzeStream(ctx, req, onChunk)
}
