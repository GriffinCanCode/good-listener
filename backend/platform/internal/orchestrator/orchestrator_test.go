package orchestrator

import (
	"encoding/binary"
	"math"
	"strings"
	"testing"
	"time"
)

func TestFloat32ToBytes(t *testing.T) {
	samples := []float32{0.0, 1.0, -1.0, 0.5}
	bytes := float32ToBytes(samples)

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

func TestTranscriptEntry(t *testing.T) {
	entry := transcriptEntry{
		timestamp: time.Now(),
		text:      "Hello world",
		source:    "user",
	}

	if entry.text != "Hello world" {
		t.Errorf("text = %q, want %q", entry.text, "Hello world")
	}
	if entry.source != "user" {
		t.Errorf("source = %q, want %q", entry.source, "user")
	}
}

func TestVADState(t *testing.T) {
	state := &vadState{
		buffer:        make([]float32, 0),
		speechBuffer:  make([]float32, 0),
		isSpeaking:    false,
		silenceChunks: 0,
	}

	// Test initial state
	if state.isSpeaking {
		t.Error("isSpeaking should be false initially")
	}
	if state.silenceChunks != 0 {
		t.Errorf("silenceChunks = %d, want 0", state.silenceChunks)
	}

	// Test adding to buffer
	state.buffer = append(state.buffer, 0.1, 0.2, 0.3)
	if len(state.buffer) != 3 {
		t.Errorf("buffer length = %d, want 3", len(state.buffer))
	}

	// Test speech detection simulation
	state.isSpeaking = true
	state.speechBuffer = append(state.speechBuffer, state.buffer...)
	if len(state.speechBuffer) != 3 {
		t.Errorf("speechBuffer length = %d, want 3", len(state.speechBuffer))
	}
}

func TestTranscriptEvent(t *testing.T) {
	event := TranscriptEvent{
		Text:   "Test transcript",
		Source: "system",
	}

	if event.Text != "Test transcript" {
		t.Errorf("Text = %q, want %q", event.Text, "Test transcript")
	}
	if event.Source != "system" {
		t.Errorf("Source = %q, want %q", event.Source, "system")
	}
}

func TestGetRecentTranscriptFormatting(t *testing.T) {
	o := &Orchestrator{
		recentTranscripts: []transcriptEntry{
			{timestamp: time.Now(), text: "Hello", source: "user"},
			{timestamp: time.Now(), text: "Hi there", source: "system"},
		},
	}

	transcript := o.GetRecentTranscript(60) // last 60 seconds

	if !strings.Contains(transcript, "USER: Hello") {
		t.Error("transcript should contain 'USER: Hello'")
	}
	if !strings.Contains(transcript, "SYSTEM: Hi there") {
		t.Error("transcript should contain 'SYSTEM: Hi there'")
	}
}

func TestGetRecentTranscriptFiltering(t *testing.T) {
	oldTime := time.Now().Add(-5 * time.Minute)
	recentTime := time.Now()

	o := &Orchestrator{
		recentTranscripts: []transcriptEntry{
			{timestamp: oldTime, text: "Old message", source: "user"},
			{timestamp: recentTime, text: "Recent message", source: "user"},
		},
	}

	// Should only include messages from last 60 seconds
	transcript := o.GetRecentTranscript(60)

	if strings.Contains(transcript, "Old message") {
		t.Error("transcript should not contain old messages")
	}
	if !strings.Contains(transcript, "Recent message") {
		t.Error("transcript should contain recent messages")
	}
}

func TestSetRecording(t *testing.T) {
	o := &Orchestrator{recording: true}

	o.SetRecording(false)
	if o.recording {
		t.Error("recording should be false")
	}

	o.SetRecording(true)
	if !o.recording {
		t.Error("recording should be true")
	}
}

func TestSetAutoAnswer(t *testing.T) {
	o := &Orchestrator{autoAnswer: true}

	o.SetAutoAnswer(false)
	if o.autoAnswer {
		t.Error("autoAnswer should be false")
	}

	o.SetAutoAnswer(true)
	if !o.autoAnswer {
		t.Error("autoAnswer should be true")
	}
}

func TestGetLatestScreenText(t *testing.T) {
	o := &Orchestrator{latestScreenText: "Screen content here"}

	text := o.GetLatestScreenText()
	if text != "Screen content here" {
		t.Errorf("GetLatestScreenText = %q, want %q", text, "Screen content here")
	}
}

func TestGetLatestScreenImage(t *testing.T) {
	imageData := []byte{0xFF, 0xD8, 0xFF, 0xE0} // JPEG magic bytes
	o := &Orchestrator{latestScreenImage: imageData}

	img := o.GetLatestScreenImage()
	if len(img) != len(imageData) {
		t.Errorf("GetLatestScreenImage length = %d, want %d", len(img), len(imageData))
	}
}

func TestTranscriptEventsChannel(t *testing.T) {
	ch := make(chan TranscriptEvent, 10)
	o := &Orchestrator{transcriptCh: ch}

	// Should return the channel
	events := o.TranscriptEvents()
	if events == nil {
		t.Error("TranscriptEvents should not return nil")
	}

	// Test sending to channel
	go func() {
		ch <- TranscriptEvent{Text: "test", Source: "user"}
	}()

	select {
	case event := <-events:
		if event.Text != "test" {
			t.Errorf("event.Text = %q, want %q", event.Text, "test")
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("timeout waiting for event")
	}
}

func TestTranscriptBufferMaxSize(t *testing.T) {
	o := &Orchestrator{
		recentTranscripts: make([]transcriptEntry, 0),
	}

	// Add 35 entries (max is 30)
	for i := 0; i < 35; i++ {
		o.recentTranscripts = append(o.recentTranscripts, transcriptEntry{
			timestamp: time.Now(),
			text:      "message",
			source:    "user",
		})
		// Simulate the pruning logic
		if len(o.recentTranscripts) > 30 {
			o.recentTranscripts = o.recentTranscripts[len(o.recentTranscripts)-30:]
		}
	}

	if len(o.recentTranscripts) != 30 {
		t.Errorf("recentTranscripts length = %d, want 30", len(o.recentTranscripts))
	}
}
