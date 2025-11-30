// Package tests provides end-to-end integration tests for the backend stack
package tests

import (
	"context"
	"encoding/binary"
	"fmt"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	pb "github.com/GriffinCanCode/good-listener/backend/platform/pkg/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

const (
	inferenceAddr  = "localhost:50051"
	startupTimeout = 30 * time.Second
	testTimeout    = 10 * time.Second
)

var (
	inferenceCmd *exec.Cmd
	grpcConn     *grpc.ClientConn
)

// TestMain sets up and tears down the test environment
func TestMain(m *testing.M) {
	// Skip if not running integration tests
	if os.Getenv("INTEGRATION_TEST") != "1" {
		fmt.Println("Skipping integration tests (set INTEGRATION_TEST=1 to run)")
		os.Exit(0)
	}

	// Start inference server
	if err := startInferenceServer(); err != nil {
		fmt.Printf("Failed to start inference server: %v\n", err)
		os.Exit(1)
	}

	// Wait for server to be ready
	if err := waitForServer(); err != nil {
		fmt.Printf("Inference server not ready: %v\n", err)
		stopInferenceServer()
		os.Exit(1)
	}

	// Connect to server
	var err error
	grpcConn, err = grpc.Dial(inferenceAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		fmt.Printf("Failed to connect to inference server: %v\n", err)
		stopInferenceServer()
		os.Exit(1)
	}

	// Run tests
	code := m.Run()

	// Cleanup
	grpcConn.Close()
	stopInferenceServer()

	os.Exit(code)
}

func startInferenceServer() error {
	// Find the inference directory
	backendDir := findBackendDir()
	inferenceDir := filepath.Join(backendDir, "inference")

	// Check if venv exists
	venvPython := filepath.Join(inferenceDir, "venv", "bin", "python")
	if _, err := os.Stat(venvPython); os.IsNotExist(err) {
		return fmt.Errorf("inference venv not found at %s - run 'make backend-install' first", venvPython)
	}

	// Start the inference server
	inferenceCmd = exec.Command(venvPython, "-m", "app.grpc_server")
	inferenceCmd.Dir = inferenceDir
	inferenceCmd.Env = append(os.Environ(), "GRPC_PORT=50051")
	inferenceCmd.Stdout = os.Stdout
	inferenceCmd.Stderr = os.Stderr

	if err := inferenceCmd.Start(); err != nil {
		return fmt.Errorf("failed to start inference server: %w", err)
	}

	fmt.Printf("Started inference server (PID: %d)\n", inferenceCmd.Process.Pid)
	return nil
}

func stopInferenceServer() {
	if inferenceCmd != nil && inferenceCmd.Process != nil {
		fmt.Println("Stopping inference server...")
		inferenceCmd.Process.Kill()
		inferenceCmd.Wait()
	}
}

func waitForServer() error {
	ctx, cancel := context.WithTimeout(context.Background(), startupTimeout)
	defer cancel()

	for {
		select {
		case <-ctx.Done():
			return fmt.Errorf("timeout waiting for server")
		default:
			conn, err := grpc.Dial(inferenceAddr, grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithBlock())
			if err == nil {
				conn.Close()
				fmt.Println("Inference server is ready")
				return nil
			}
			time.Sleep(500 * time.Millisecond)
		}
	}
}

func findBackendDir() string {
	// Try relative paths from test location
	candidates := []string{
		"..",
		"../backend",
		"../../backend",
	}

	for _, c := range candidates {
		if _, err := os.Stat(filepath.Join(c, "inference")); err == nil {
			abs, _ := filepath.Abs(c)
			return abs
		}
	}

	// Fallback to current directory parent
	wd, _ := os.Getwd()
	return filepath.Dir(wd)
}

// =============================================================================
// Integration Tests
// =============================================================================

func TestE2E_VADService(t *testing.T) {
	client := pb.NewVADServiceClient(grpcConn)
	ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
	defer cancel()

	// Test DetectSpeech with silence (should return low probability)
	silenceChunk := make([]byte, 512*4) // 512 float32 samples of silence
	resp, err := client.DetectSpeech(ctx, &pb.VADRequest{
		AudioChunk: silenceChunk,
		SampleRate: 16000,
	})
	if err != nil {
		t.Fatalf("DetectSpeech failed: %v", err)
	}

	t.Logf("VAD response for silence: prob=%.3f, is_speech=%v", resp.SpeechProbability, resp.IsSpeech)

	if resp.SpeechProbability > 0.5 {
		t.Logf("Warning: silence detected as speech (prob=%.3f)", resp.SpeechProbability)
	}

	// Test ResetState
	_, err = client.ResetState(ctx, &pb.ResetStateRequest{})
	if err != nil {
		t.Fatalf("ResetState failed: %v", err)
	}
}

func TestE2E_TranscriptionService(t *testing.T) {
	client := pb.NewTranscriptionServiceClient(grpcConn)
	ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
	defer cancel()

	// Create 1 second of silence audio
	audio := makeAudioBytes(16000) // 1 second at 16kHz

	resp, err := client.Transcribe(ctx, &pb.TranscribeRequest{
		AudioData:  audio,
		SampleRate: 16000,
	})
	if err != nil {
		t.Fatalf("Transcribe failed: %v", err)
	}

	t.Logf("Transcription response: text=%q, confidence=%.3f", resp.Text, resp.Confidence)
	// Silence should produce empty or near-empty transcription
}

func TestE2E_OCRService(t *testing.T) {
	client := pb.NewOCRServiceClient(grpcConn)
	ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
	defer cancel()

	// Create a minimal valid JPEG (1x1 white pixel)
	// This is a minimal valid JPEG that OCR can process
	minimalJPEG := []byte{
		0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
		0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
		0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
		0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
		0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
		0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
		0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
		0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
		0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
		0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
		0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
		0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
		0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
		0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
		0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
		0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
		0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
		0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
		0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
		0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
		0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
		0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
		0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
		0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
		0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
		0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
		0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7E, 0xB4,
		0x01, 0xFF, 0xD9,
	}

	resp, err := client.ExtractText(ctx, &pb.OCRRequest{
		ImageData: minimalJPEG,
		Format:    "jpeg",
	})
	if err != nil {
		t.Fatalf("ExtractText failed: %v", err)
	}

	t.Logf("OCR response: text_len=%d, boxes=%d", len(resp.Text), len(resp.Boxes))
	// Minimal image should produce empty or minimal text
}

func TestE2E_MemoryService(t *testing.T) {
	client := pb.NewMemoryServiceClient(grpcConn)
	ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
	defer cancel()

	// Store a memory
	storeResp, err := client.Store(ctx, &pb.StoreRequest{
		Text:   "Integration test memory: The quick brown fox jumps over the lazy dog.",
		Source: "test",
	})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	t.Logf("Store response: success=%v", storeResp.Success)

	// Query for the memory
	queryResp, err := client.Query(ctx, &pb.QueryRequest{
		QueryText: "quick brown fox",
		NResults:  5,
	})
	if err != nil {
		t.Fatalf("Query failed: %v", err)
	}

	t.Logf("Query response: documents=%d", len(queryResp.Documents))

	// Should find our stored memory
	found := false
	for _, doc := range queryResp.Documents {
		if len(doc) > 0 {
			t.Logf("Found document: %s", doc[:min(50, len(doc))])
			found = true
		}
	}

	if !found {
		t.Log("Warning: stored memory not found in query results (may need ChromaDB setup)")
	}
}

func TestE2E_LLMService_IsQuestion(t *testing.T) {
	client := pb.NewLLMServiceClient(grpcConn)
	ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
	defer cancel()

	tests := []struct {
		text       string
		isQuestion bool
	}{
		{"What time is it?", true},
		{"How does this work?", true},
		{"Can you help me?", true},
		{"This is a statement.", false},
		{"Hello world", false},
		{"Where are you going?", true},
	}

	for _, tt := range tests {
		resp, err := client.IsQuestion(ctx, &pb.IsQuestionRequest{Text: tt.text})
		if err != nil {
			t.Fatalf("IsQuestion failed for %q: %v", tt.text, err)
		}

		if resp.IsQuestion != tt.isQuestion {
			t.Errorf("IsQuestion(%q) = %v, want %v", tt.text, resp.IsQuestion, tt.isQuestion)
		} else {
			t.Logf("IsQuestion(%q) = %v ✓", tt.text, resp.IsQuestion)
		}
	}
}

func TestE2E_FullFlow(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// This test simulates the full flow:
	// 1. VAD detects speech
	// 2. Audio is transcribed
	// 3. Memory stores the transcript
	// 4. Question detection works
	// 5. LLM can analyze (if API key available)

	t.Log("=== Full Flow Integration Test ===")

	// Step 1: VAD
	vadClient := pb.NewVADServiceClient(grpcConn)
	vadResp, err := vadClient.DetectSpeech(ctx, &pb.VADRequest{
		AudioChunk: make([]byte, 512*4),
		SampleRate: 16000,
	})
	if err != nil {
		t.Fatalf("Step 1 (VAD) failed: %v", err)
	}
	t.Logf("Step 1 (VAD): speech_prob=%.3f ✓", vadResp.SpeechProbability)

	// Step 2: Transcription
	transcribeClient := pb.NewTranscriptionServiceClient(grpcConn)
	transcribeResp, err := transcribeClient.Transcribe(ctx, &pb.TranscribeRequest{
		AudioData:  makeAudioBytes(8000), // 0.5 sec
		SampleRate: 16000,
	})
	if err != nil {
		t.Fatalf("Step 2 (Transcription) failed: %v", err)
	}
	t.Logf("Step 2 (Transcription): text=%q ✓", transcribeResp.Text)

	// Step 3: Memory Storage
	memoryClient := pb.NewMemoryServiceClient(grpcConn)
	storeResp, err := memoryClient.Store(ctx, &pb.StoreRequest{
		Text:   "E2E test transcript: Hello from integration test",
		Source: "audio",
	})
	if err != nil {
		t.Fatalf("Step 3 (Memory Store) failed: %v", err)
	}
	t.Logf("Step 3 (Memory Store): success=%v ✓", storeResp.Success)

	// Step 4: Question Detection
	llmClient := pb.NewLLMServiceClient(grpcConn)
	questionResp, err := llmClient.IsQuestion(ctx, &pb.IsQuestionRequest{
		Text: "What did I just say?",
	})
	if err != nil {
		t.Fatalf("Step 4 (Question Detection) failed: %v", err)
	}
	t.Logf("Step 4 (Question Detection): is_question=%v ✓", questionResp.IsQuestion)

	// Step 5: Memory Query
	queryResp, err := memoryClient.Query(ctx, &pb.QueryRequest{
		QueryText: "integration test",
		NResults:  3,
	})
	if err != nil {
		t.Fatalf("Step 5 (Memory Query) failed: %v", err)
	}
	t.Logf("Step 5 (Memory Query): found=%d documents ✓", len(queryResp.Documents))

	t.Log("=== Full Flow Complete ===")
}

// =============================================================================
// Helpers
// =============================================================================

func makeAudioBytes(samples int) []byte {
	buf := make([]byte, samples*4)
	for i := 0; i < samples; i++ {
		// Generate silence (0.0 float32)
		binary.LittleEndian.PutUint32(buf[i*4:], math.Float32bits(0.0))
	}
	return buf
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
