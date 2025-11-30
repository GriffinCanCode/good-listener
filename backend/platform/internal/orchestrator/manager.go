// Package orchestrator coordinates audio, screen, and inference services
package orchestrator

import (
	"context"
	"strings"
	"sync"
	"time"

	audiocap "github.com/GriffinCanCode/good-listener/backend/platform/internal/audio"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/config"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/grpcclient"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/audio"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/autoanswer"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/memory"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/screen"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/transcript"
	screencap "github.com/GriffinCanCode/good-listener/backend/platform/internal/screen"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/trace"
	pb "github.com/GriffinCanCode/good-listener/backend/platform/pkg/pb"
)

// TranscriptEvent re-exported for API compatibility.
type TranscriptEvent = transcript.Event

// AutoAnswerEvent represents an auto-answer streaming event.
type AutoAnswerEvent struct {
	Type     string // "start", "chunk", "done"
	Question string // Only for "start"
	Content  string // Only for "chunk"
}

// VADEvent represents a voice activity detection event.
type VADEvent struct {
	Probability float32 `json:"probability"`
	IsSpeech    bool    `json:"is_speech"`
	Source      string  `json:"source"` // "user" or "system"
}

// Orchestrator is an alias for Manager (backwards compatibility).
type Orchestrator = Manager

// Manager coordinates all services.
type Manager struct {
	inference *grpcclient.Client
	cfg       *config.Config

	audioCap       *audiocap.Capturer
	audioProc      *audio.Processor
	screenProc     *screen.Processor
	transcripts    *transcript.MemoryStore
	autoAnswer     *autoanswer.Detector
	autoAnswerChan chan AutoAnswerEvent
	vadChan        chan VADEvent
	memBatcher     *memory.Batcher

	mu        sync.RWMutex
	recording bool
	stopCh    chan struct{}
}

// New creates a new manager.
func New(inference *grpcclient.Client, cfg *config.Config) *Manager {
	log := trace.Logger(context.Background())
	audioCap, err := audiocap.NewCapturer(cfg.Audio.SampleRate, AudioBufferSize, cfg.Audio.CaptureSystemAudio, cfg.Audio.ExcludedDevices)
	if err != nil {
		log.Error("failed to create audio capturer", "error", err)
	}

	transcripts := transcript.NewStore(TranscriptMaxEntries, TranscriptEventBuffer)
	autoAnswerDet := autoanswer.NewDetector(inference, cfg.AutoAnswer.CooldownSeconds, cfg.AutoAnswer.Enabled)
	memBatcher := memory.NewBatcher(inference, MemoryBatcherMaxSize, MemoryBatcherFlushDelay)

	m := &Manager{
		inference:      inference,
		cfg:            cfg,
		audioCap:       audioCap,
		transcripts:    transcripts,
		autoAnswer:     autoAnswerDet,
		autoAnswerChan: make(chan AutoAnswerEvent, AutoAnswerChannelBuffer),
		vadChan:        make(chan VADEvent, VADChannelBuffer),
		memBatcher:     memBatcher,
		recording:      true,
		stopCh:         make(chan struct{}),
	}

	// Create audio processor with speech and VAD handlers
	if audioCap != nil {
		m.audioProc = audio.NewProcessor(inference, audio.Config{
			SampleRate:       cfg.Audio.SampleRate,
			VADThreshold:     cfg.Audio.VADThreshold,
			MaxSilenceChunks: cfg.Audio.MaxSilenceChunks,
		}, m.handleSpeech, m.handleVAD)
	}

	// Create screen processor with batched memory client
	m.screenProc = screen.NewProcessor(screencap.New(), inference, m)

	return m
}

// StoreMemory implements screen.MemoryClient using the batcher.
func (m *Manager) StoreMemory(_ context.Context, text, source string) error {
	m.mu.RLock()
	recording := m.recording
	m.mu.RUnlock()
	if !recording {
		return nil
	}
	m.memBatcher.Add(text, source)
	return nil
}

// handleSpeech processes completed speech segments.
func (m *Manager) handleSpeech(ctx context.Context, samples []float32, source string) {
	ctx, span := trace.StartSpan(ctx, "handle_speech")
	defer span.End()
	span.SetAttr("source", source)
	span.SetAttr("samples", len(samples))

	log := trace.Logger(ctx)
	audioBytes := audio.Float32ToBytes(samples)
	text, err := m.inference.Transcribe(ctx, audioBytes, int32(m.cfg.Audio.SampleRate))
	if err != nil {
		span.SetAttr("error", err.Error())
		log.Error("transcription error", "error", err)
		return
	}

	text = strings.TrimSpace(text)
	if text == "" {
		return
	}

	// Derive speaker label from source
	speaker := "Speaker"
	if source == "user" {
		speaker = "You"
	}

	log.Info("transcribed", "source", source, "speaker", speaker, "text", text)

	m.transcripts.Add(text, source, speaker)
	m.transcripts.Emit(TranscriptEvent{Text: text, Source: source, Speaker: speaker})

	// Store to vector DB if recording (batched for efficiency)
	m.mu.RLock()
	shouldStore := m.recording && len(strings.Fields(text)) >= MinWordsForMemoryStorage
	m.mu.RUnlock()

	if shouldStore {
		m.memBatcher.Add(source+": "+text, "audio")
	}

	// Check for auto-answer on system audio
	if source == "system" && m.autoAnswer.Check(ctx, text) {
		go m.streamAutoAnswer(ctx, text)
	}
}

// TranscriptEvents returns channel for transcript events.
func (m *Manager) TranscriptEvents() <-chan TranscriptEvent {
	return m.transcripts.Events()
}

// AutoAnswerEvents returns channel for auto-answer events.
func (m *Manager) AutoAnswerEvents() <-chan AutoAnswerEvent {
	return m.autoAnswerChan
}

// VADEvents returns channel for VAD probability events.
func (m *Manager) VADEvents() <-chan VADEvent {
	return m.vadChan
}

// handleVAD sends VAD events to the channel (non-blocking).
func (m *Manager) handleVAD(prob float32, isSpeech bool, source string) {
	select {
	case m.vadChan <- VADEvent{Probability: prob, IsSpeech: isSpeech, Source: source}:
	default: // Drop if buffer full to avoid blocking audio processing
	}
}

// streamAutoAnswer generates and streams an LLM response for a detected question.
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
		Transcript:  m.GetRecentTranscript(AutoAnswerTranscriptSeconds),
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

// Start begins orchestration.
func (m *Manager) Start(ctx context.Context) error {
	log := trace.Logger(ctx)
	if m.audioCap != nil {
		if err := m.audioCap.Start(ctx); err != nil {
			log.Warn("audio capture start failed", "error", err)
		}
		go m.audioLoop(ctx)
	}

	go m.screenProc.Run(ctx, m.cfg.Screen.CaptureRate, m.stopCh)
	go m.vadCleanupLoop(ctx)
	go m.summarizationLoop(ctx)

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
	ticker := time.NewTicker(VADCleanupInterval)
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

func (m *Manager) summarizationLoop(ctx context.Context) {
	ticker := time.NewTicker(SummarizationInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-m.stopCh:
			return
		case <-ticker.C:
			m.summarizeOldTranscripts(ctx)
		}
	}
}

func (m *Manager) summarizeOldTranscripts(ctx context.Context) {
	// Skip if not recording (no new context needed)
	m.mu.RLock()
	recording := m.recording
	m.mu.RUnlock()
	if !recording {
		return
	}

	entries, start, end := m.transcripts.GetUnsummarized(SummarizationThreshold)
	if len(entries) < SummarizationMinEntries {
		return
	}

	// Build transcript text from entries
	var parts []string
	for _, e := range entries {
		parts = append(parts, strings.ToUpper(e.Source)+": "+e.Text)
	}
	text := strings.Join(parts, "\n")

	ctx, span := trace.StartSpan(ctx, "summarize_transcript")
	defer span.End()
	span.SetAttr("entries", len(entries))
	span.SetAttr("text_len", len(text))

	// Add timeout to prevent blocking
	ctx, cancel := context.WithTimeout(ctx, SummarizationTimeout)
	defer cancel()

	summary, err := m.inference.SummarizeTranscript(ctx, text, SummarizationMaxLength)
	if err != nil {
		span.SetAttr("error", err.Error())
		trace.Logger(ctx).Warn("summarization failed", "error", err)
		return
	}

	m.transcripts.StoreSummary(start, end, summary)
	span.SetAttr("summary_len", len(summary))
	trace.Logger(ctx).Info("transcript summarized", "entries", len(entries), "original_len", len(text), "summary_len", len(summary))
}

// Stop stops orchestration.
func (m *Manager) Stop() {
	close(m.stopCh)
	if m.audioCap != nil {
		m.audioCap.Stop()
	}
	if m.audioProc != nil {
		m.audioProc.Reset()
	}
	if m.memBatcher != nil {
		m.memBatcher.Stop()
	}
}

// GetRecentTranscript returns transcript from last N seconds.
func (m *Manager) GetRecentTranscript(seconds int) string {
	return m.transcripts.GetRecent(seconds)
}

// GetLatestScreenText returns the latest OCR text.
func (m *Manager) GetLatestScreenText() string {
	return m.screenProc.Text()
}

// GetLatestScreenImage returns the latest screenshot.
func (m *Manager) GetLatestScreenImage() []byte {
	return m.screenProc.Image()
}

// SetRecording enables/disables memory recording.
func (m *Manager) SetRecording(enabled bool) {
	m.mu.Lock()
	m.recording = enabled
	m.mu.Unlock()
	m.screenProc.SetRecording(enabled)
	trace.Logger(context.Background()).Info("recording state changed", "enabled", enabled)
}

// SetAutoAnswer enables/disables auto-answering.
func (m *Manager) SetAutoAnswer(enabled bool) {
	m.autoAnswer.SetEnabled(enabled)
}

// Analyze sends a query to the LLM.
func (m *Manager) Analyze(ctx context.Context, query string, onChunk func(string)) error {
	ctx, span := trace.StartSpan(ctx, "orchestrator_analyze")
	defer span.End()
	span.SetAttr("query_len", len(query))

	req := &pb.AnalyzeRequest{
		UserQuery:   query,
		Transcript:  m.GetRecentTranscript(AnalyzeTranscriptSeconds),
		ContextText: m.GetLatestScreenText(),
		ImageData:   m.GetLatestScreenImage(),
	}
	return m.inference.AnalyzeStream(ctx, req, onChunk)
}
