package grpcclient

import (
	"testing"
	"time"

	"github.com/good-listener/platform/internal/resilience"
	pb "github.com/good-listener/platform/pkg/pb"
)

func TestCircuitBreakerInitialState(t *testing.T) {
	cb := resilience.New(resilience.DefaultConfig())
	if cb.State() != resilience.Closed {
		t.Errorf("initial state = %v, want Closed", cb.State())
	}
}

func TestCircuitBreakerOpensAfterThreshold(t *testing.T) {
	cb := resilience.New(resilience.Config{
		Threshold:         3,
		ResetTimeout:      time.Second,
		HalfOpenSuccesses: 2,
	})

	for i := 0; i < 3; i++ {
		cb.Failure()
	}

	if cb.State() != resilience.Open {
		t.Errorf("state after %d failures = %v, want Open", 3, cb.State())
	}
}

func TestCircuitBreakerRejectsWhenOpen(t *testing.T) {
	cb := resilience.New(resilience.Config{
		Threshold:         1,
		ResetTimeout:      time.Hour,
		HalfOpenSuccesses: 1,
	})
	cb.Failure()

	if err := cb.Allow(); err != resilience.ErrOpen {
		t.Errorf("Allow() = %v, want ErrOpen", err)
	}
}

func TestCircuitBreakerTransitionsToHalfOpen(t *testing.T) {
	cb := resilience.New(resilience.Config{
		Threshold:         1,
		ResetTimeout:      time.Millisecond,
		HalfOpenSuccesses: 1,
	})
	cb.Failure()

	time.Sleep(5 * time.Millisecond)

	if err := cb.Allow(); err != nil {
		t.Errorf("Allow() after reset timeout = %v, want nil", err)
	}
	if cb.State() != resilience.HalfOpen {
		t.Errorf("state after reset timeout = %v, want HalfOpen", cb.State())
	}
}

func TestCircuitBreakerClosesAfterSuccesses(t *testing.T) {
	cb := resilience.New(resilience.Config{
		Threshold:         1,
		ResetTimeout:      time.Millisecond,
		HalfOpenSuccesses: 2,
	})
	cb.Failure()

	time.Sleep(5 * time.Millisecond)
	_ = cb.Allow() // transition to half-open

	cb.Success()
	cb.Success()

	if cb.State() != resilience.Closed {
		t.Errorf("state after successes = %v, want Closed", cb.State())
	}
}

func TestCircuitBreakerReopensOnFailureInHalfOpen(t *testing.T) {
	cb := resilience.New(resilience.Config{
		Threshold:         1,
		ResetTimeout:      time.Millisecond,
		HalfOpenSuccesses: 3,
	})
	cb.Failure()

	time.Sleep(5 * time.Millisecond)
	_ = cb.Allow() // transition to half-open

	cb.Failure()

	if cb.State() != resilience.Open {
		t.Errorf("state after failure in half-open = %v, want Open", cb.State())
	}
}

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg.KeepaliveTime != 10*time.Second {
		t.Errorf("KeepaliveTime = %v, want 10s", cfg.KeepaliveTime)
	}
	if cfg.KeepaliveTimeout != 3*time.Second {
		t.Errorf("KeepaliveTimeout = %v, want 3s", cfg.KeepaliveTimeout)
	}
	if cfg.HealthCheckInterval != 5*time.Second {
		t.Errorf("HealthCheckInterval = %v, want 5s", cfg.HealthCheckInterval)
	}
}

func TestBackwardsCompatibility(t *testing.T) {
	// Test type aliases work correctly
	if CircuitClosed != resilience.Closed {
		t.Error("CircuitClosed != resilience.Closed")
	}
	if CircuitOpen != resilience.Open {
		t.Error("CircuitOpen != resilience.Open")
	}
	if CircuitHalfOpen != resilience.HalfOpen {
		t.Error("CircuitHalfOpen != resilience.HalfOpen")
	}

	// Test error alias
	if ErrCircuitOpen != resilience.ErrOpen {
		t.Error("ErrCircuitOpen != resilience.ErrOpen")
	}
}

func TestTranscribeRequest(t *testing.T) {
	audio := []byte{0, 0, 0, 0} // 1 float32 sample
	req := &pb.TranscribeRequest{
		AudioData:  audio,
		SampleRate: 16000,
		Language:   "en",
	}

	if len(req.AudioData) != 4 {
		t.Errorf("AudioData length = %d, want 4", len(req.AudioData))
	}
	if req.SampleRate != 16000 {
		t.Errorf("SampleRate = %d, want 16000", req.SampleRate)
	}
	if req.Language != "en" {
		t.Errorf("Language = %q, want %q", req.Language, "en")
	}
}

func TestTranscribeResponse(t *testing.T) {
	resp := &pb.TranscribeResponse{
		Text:       "Hello world",
		Confidence: 0.95,
		DurationMs: 1000,
	}

	if resp.Text != "Hello world" {
		t.Errorf("Text = %q, want %q", resp.Text, "Hello world")
	}
	if resp.Confidence != 0.95 {
		t.Errorf("Confidence = %f, want %f", resp.Confidence, 0.95)
	}
	if resp.DurationMs != 1000 {
		t.Errorf("DurationMs = %d, want %d", resp.DurationMs, 1000)
	}
}

func TestVADRequest(t *testing.T) {
	chunk := make([]byte, 512*4) // 512 float32 samples
	req := &pb.VADRequest{
		AudioChunk: chunk,
		SampleRate: 16000,
	}

	if len(req.AudioChunk) != 512*4 {
		t.Errorf("AudioChunk length = %d, want %d", len(req.AudioChunk), 512*4)
	}
	if req.SampleRate != 16000 {
		t.Errorf("SampleRate = %d, want %d", req.SampleRate, 16000)
	}
}

func TestVADResponse(t *testing.T) {
	resp := &pb.VADResponse{
		SpeechProbability: 0.8,
		IsSpeech:          true,
	}

	if resp.SpeechProbability != 0.8 {
		t.Errorf("SpeechProbability = %f, want %f", resp.SpeechProbability, 0.8)
	}
	if !resp.IsSpeech {
		t.Error("IsSpeech should be true")
	}
}

func TestOCRRequest(t *testing.T) {
	imageData := []byte{0xFF, 0xD8, 0xFF, 0xE0} // JPEG magic bytes
	req := &pb.OCRRequest{
		ImageData: imageData,
		Format:    "jpeg",
	}

	if len(req.ImageData) != 4 {
		t.Errorf("ImageData length = %d, want 4", len(req.ImageData))
	}
	if req.Format != "jpeg" {
		t.Errorf("Format = %q, want %q", req.Format, "jpeg")
	}
}

func TestOCRResponse(t *testing.T) {
	resp := &pb.OCRResponse{
		Text: "[0, 0, 100, 20] Hello World",
		Boxes: []*pb.BoundingBox{
			{X1: 0, Y1: 0, X2: 100, Y2: 20, Text: "Hello World", Confidence: 0.95},
		},
	}

	if resp.Text == "" {
		t.Error("Text should not be empty")
	}
	if len(resp.Boxes) != 1 {
		t.Errorf("Boxes length = %d, want 1", len(resp.Boxes))
	}
	if resp.Boxes[0].Text != "Hello World" {
		t.Errorf("Box text = %q, want %q", resp.Boxes[0].Text, "Hello World")
	}
}

func TestAnalyzeRequest(t *testing.T) {
	req := &pb.AnalyzeRequest{
		ContextText: "Screen content",
		UserQuery:   "What's on my screen?",
		ImageData:   []byte{0xFF, 0xD8},
		Transcript:  "USER: Hello\nSYSTEM: Hi",
	}

	if req.ContextText != "Screen content" {
		t.Errorf("ContextText = %q, want %q", req.ContextText, "Screen content")
	}
	if req.UserQuery != "What's on my screen?" {
		t.Errorf("UserQuery = %q, want %q", req.UserQuery, "What's on my screen?")
	}
	if len(req.ImageData) != 2 {
		t.Errorf("ImageData length = %d, want 2", len(req.ImageData))
	}
}

func TestAnalyzeChunk(t *testing.T) {
	chunk := &pb.AnalyzeChunk{
		Content: "Here's what I see...",
		IsFinal: false,
	}

	if chunk.Content != "Here's what I see..." {
		t.Errorf("Content = %q, want %q", chunk.Content, "Here's what I see...")
	}
	if chunk.IsFinal {
		t.Error("IsFinal should be false")
	}

	finalChunk := &pb.AnalyzeChunk{Content: "", IsFinal: true}
	if !finalChunk.IsFinal {
		t.Error("IsFinal should be true for final chunk")
	}
}

func TestStoreRequest(t *testing.T) {
	req := &pb.StoreRequest{
		Text:     "Memory content",
		Source:   "audio",
		Metadata: map[string]string{"key": "value"},
	}

	if req.Text != "Memory content" {
		t.Errorf("Text = %q, want %q", req.Text, "Memory content")
	}
	if req.Source != "audio" {
		t.Errorf("Source = %q, want %q", req.Source, "audio")
	}
	if req.Metadata["key"] != "value" {
		t.Errorf("Metadata[key] = %q, want %q", req.Metadata["key"], "value")
	}
}

func TestQueryRequest(t *testing.T) {
	req := &pb.QueryRequest{
		QueryText:    "search query",
		NResults:     5,
		SourceFilter: "audio",
	}

	if req.QueryText != "search query" {
		t.Errorf("QueryText = %q, want %q", req.QueryText, "search query")
	}
	if req.NResults != 5 {
		t.Errorf("NResults = %d, want %d", req.NResults, 5)
	}
	if req.SourceFilter != "audio" {
		t.Errorf("SourceFilter = %q, want %q", req.SourceFilter, "audio")
	}
}

func TestQueryResponse(t *testing.T) {
	resp := &pb.QueryResponse{
		Documents: []string{"doc1", "doc2"},
		Scores:    []float32{0.9, 0.8},
	}

	if len(resp.Documents) != 2 {
		t.Errorf("Documents length = %d, want 2", len(resp.Documents))
	}
	if resp.Documents[0] != "doc1" {
		t.Errorf("Documents[0] = %q, want %q", resp.Documents[0], "doc1")
	}
	if len(resp.Scores) != 2 {
		t.Errorf("Scores length = %d, want 2", len(resp.Scores))
	}
}

func TestIsQuestionRequest(t *testing.T) {
	req := &pb.IsQuestionRequest{Text: "What time is it?"}

	if req.Text != "What time is it?" {
		t.Errorf("Text = %q, want %q", req.Text, "What time is it?")
	}
}

func TestIsQuestionResponse(t *testing.T) {
	resp := &pb.IsQuestionResponse{IsQuestion: true}

	if !resp.IsQuestion {
		t.Error("IsQuestion should be true")
	}
}
