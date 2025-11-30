package orchestrator

import (
	"strings"
	"testing"
	"time"

	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/audio"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator/transcript"
)

func TestFloat32ToBytes(t *testing.T) {
	samples := []float32{0.0, 1.0, -1.0, 0.5}
	bytes := audio.Float32ToBytes(samples)

	if len(bytes) != len(samples)*4 {
		t.Errorf("byte length = %d, want %d", len(bytes), len(samples)*4)
	}
}

func TestTranscriptStore(t *testing.T) {
	store := transcript.NewStore(30, 10)

	store.Add("Hello world", "user", "You")
	entries := store.Entries()

	if len(entries) != 1 {
		t.Errorf("entries length = %d, want 1", len(entries))
	}
	if entries[0].Text != "Hello world" {
		t.Errorf("text = %q, want %q", entries[0].Text, "Hello world")
	}
	if entries[0].Source != "user" {
		t.Errorf("source = %q, want %q", entries[0].Source, "user")
	}
}

func TestTranscriptStoreMaxSize(t *testing.T) {
	store := transcript.NewStore(30, 10)

	for i := 0; i < 35; i++ {
		store.Add("message", "user", "You")
	}

	entries := store.Entries()
	if len(entries) != 30 {
		t.Errorf("entries length = %d, want 30", len(entries))
	}
}

func TestTranscriptGetRecent(t *testing.T) {
	store := transcript.NewStore(30, 10)
	store.Add("Hello", "user", "You")
	store.Add("Hi there", "system", "Speaker")

	recent := store.GetRecent(60)

	if !strings.Contains(recent, "USER: Hello") {
		t.Error("transcript should contain 'USER: Hello'")
	}
	if !strings.Contains(recent, "SYSTEM: Hi there") {
		t.Error("transcript should contain 'SYSTEM: Hi there'")
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

func TestTranscriptEmit(t *testing.T) {
	store := transcript.NewStore(30, 10)

	go func() {
		store.Emit(transcript.Event{Text: "test", Source: "user"})
	}()

	select {
	case event := <-store.Events():
		if event.Text != "test" {
			t.Errorf("event.Text = %q, want %q", event.Text, "test")
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("timeout waiting for event")
	}
}

func TestManagerSetRecording(t *testing.T) {
	m := &Manager{recording: true}

	m.mu.Lock()
	m.recording = false
	m.mu.Unlock()

	m.mu.RLock()
	if m.recording {
		t.Error("recording should be false")
	}
	m.mu.RUnlock()
}
