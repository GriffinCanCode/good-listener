package server

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/GriffinCanCode/good-listener/backend/platform/internal/config"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator"
)

// mockOrchestrator for testing.
type mockOrchestrator struct {
	screenText    string
	screenImage   []byte
	transcript    string
	recordingOn   bool
	autoAnswerOn  bool
	transcriptsCh chan orchestrator.TranscriptEvent
}

func newMockOrchestrator() *mockOrchestrator {
	return &mockOrchestrator{
		screenText:    "Test screen text",
		transcript:    "USER: Hello\nSYSTEM: Hi there",
		transcriptsCh: make(chan orchestrator.TranscriptEvent, 10),
	}
}

func (m *mockOrchestrator) GetLatestScreenText() string    { return m.screenText }
func (m *mockOrchestrator) GetLatestScreenImage() []byte   { return m.screenImage }
func (m *mockOrchestrator) GetRecentTranscript(int) string { return m.transcript }
func (m *mockOrchestrator) SetRecording(enabled bool)      { m.recordingOn = enabled }
func (m *mockOrchestrator) SetAutoAnswer(enabled bool)     { m.autoAnswerOn = enabled }
func (m *mockOrchestrator) TranscriptEvents() <-chan orchestrator.TranscriptEvent {
	return m.transcriptsCh
}

func TestCORSMiddleware(t *testing.T) {
	handler := corsMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// Test OPTIONS request
	req := httptest.NewRequest("OPTIONS", "/test", http.NoBody)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("OPTIONS status = %d, want %d", rec.Code, http.StatusOK)
	}
	if v := rec.Header().Get("Access-Control-Allow-Origin"); v != "*" {
		t.Errorf("CORS origin = %q, want %q", v, "*")
	}
	if v := rec.Header().Get("Access-Control-Allow-Methods"); v != "GET, POST, OPTIONS" {
		t.Errorf("CORS methods = %q, want %q", v, "GET, POST, OPTIONS")
	}

	// Test regular request
	req = httptest.NewRequest("GET", "/test", http.NoBody)
	rec = httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("GET status = %d, want %d", rec.Code, http.StatusOK)
	}
	if v := rec.Header().Get("Access-Control-Allow-Origin"); v != "*" {
		t.Errorf("CORS origin on GET = %q, want %q", v, "*")
	}
}

func TestMessageTypes(t *testing.T) {
	// Test message serialization
	tests := []struct {
		name    string
		msg     interface{}
		typeVal string
	}{
		{
			"transcript",
			TranscriptMessage{Type: "transcript", Text: "Hello", Source: "user"},
			"transcript",
		},
		{
			"chunk",
			ChunkMessage{Type: "chunk", Content: "response text"},
			"chunk",
		},
		{
			"start",
			StartMessage{Type: "start", Role: "assistant"},
			"start",
		},
		{
			"done",
			DoneMessage{Type: "done"},
			"done",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			data, err := json.Marshal(tt.msg)
			if err != nil {
				t.Fatalf("json.Marshal error: %v", err)
			}

			var base Message
			if err := json.Unmarshal(data, &base); err != nil {
				t.Fatalf("json.Unmarshal error: %v", err)
			}

			if base.Type != tt.typeVal {
				t.Errorf("type = %q, want %q", base.Type, tt.typeVal)
			}
		})
	}
}

func TestChatMessageParsing(t *testing.T) {
	input := `{"type": "chat", "message": "What's on my screen?"}`

	var chat ChatMessage
	if err := json.Unmarshal([]byte(input), &chat); err != nil {
		t.Fatalf("json.Unmarshal error: %v", err)
	}

	if chat.Type != "chat" {
		t.Errorf("type = %q, want %q", chat.Type, "chat")
	}
	if chat.Message != "What's on my screen?" {
		t.Errorf("message = %q, want %q", chat.Message, "What's on my screen?")
	}
}

func TestServerConfig(t *testing.T) {
	cfg := &config.Config{
		Platform: config.PlatformConfig{
			HTTPAddr:      ":8000",
			InferenceAddr: "localhost:50051",
		},
	}

	if cfg.Platform.HTTPAddr != ":8000" {
		t.Errorf("Platform.HTTPAddr = %q, want %q", cfg.Platform.HTTPAddr, ":8000")
	}
	if cfg.Platform.InferenceAddr != "localhost:50051" {
		t.Errorf("Platform.InferenceAddr = %q, want %q", cfg.Platform.InferenceAddr, "localhost:50051")
	}
}

func TestTranscriptMessage(t *testing.T) {
	msg := TranscriptMessage{
		Type:   "transcript",
		Text:   "Hello world",
		Source: "user",
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("json.Marshal error: %v", err)
	}

	var decoded TranscriptMessage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("json.Unmarshal error: %v", err)
	}

	if decoded.Type != "transcript" {
		t.Errorf("Type = %q, want %q", decoded.Type, "transcript")
	}
	if decoded.Text != "Hello world" {
		t.Errorf("Text = %q, want %q", decoded.Text, "Hello world")
	}
	if decoded.Source != "user" {
		t.Errorf("Source = %q, want %q", decoded.Source, "user")
	}
}
