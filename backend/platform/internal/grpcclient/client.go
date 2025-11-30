// Package grpcclient provides a client for the Python inference gRPC server
package grpcclient

import (
	"context"
	"io"
	"log/slog"

	pb "github.com/good-listener/platform/pkg/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// Client wraps all inference service clients
type Client struct {
	conn          *grpc.ClientConn
	Transcription pb.TranscriptionServiceClient
	VAD           pb.VADServiceClient
	OCR           pb.OCRServiceClient
	LLM           pb.LLMServiceClient
	Memory        pb.MemoryServiceClient
}

// New creates a new inference client
func New(addr string) (*Client, error) {
	conn, err := grpc.Dial(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, err
	}

	return &Client{
		conn:          conn,
		Transcription: pb.NewTranscriptionServiceClient(conn),
		VAD:           pb.NewVADServiceClient(conn),
		OCR:           pb.NewOCRServiceClient(conn),
		LLM:           pb.NewLLMServiceClient(conn),
		Memory:        pb.NewMemoryServiceClient(conn),
	}, nil
}

// Close closes the gRPC connection
func (c *Client) Close() error {
	return c.conn.Close()
}

// Transcribe sends audio for transcription
func (c *Client) Transcribe(ctx context.Context, audio []byte, sampleRate int32) (string, error) {
	resp, err := c.Transcription.Transcribe(ctx, &pb.TranscribeRequest{
		AudioData:  audio,
		SampleRate: sampleRate,
	})
	if err != nil {
		return "", err
	}
	return resp.Text, nil
}

// DetectSpeech checks if audio chunk contains speech
func (c *Client) DetectSpeech(ctx context.Context, audio []byte, sampleRate int32) (float32, bool, error) {
	resp, err := c.VAD.DetectSpeech(ctx, &pb.VADRequest{
		AudioChunk: audio,
		SampleRate: sampleRate,
	})
	if err != nil {
		return 0, false, err
	}
	return resp.SpeechProbability, resp.IsSpeech, nil
}

// ResetVAD resets VAD model state
func (c *Client) ResetVAD(ctx context.Context) error {
	_, err := c.VAD.ResetState(ctx, &pb.ResetStateRequest{})
	return err
}

// ExtractText performs OCR on an image
func (c *Client) ExtractText(ctx context.Context, imageData []byte, format string) (string, error) {
	resp, err := c.OCR.ExtractText(ctx, &pb.OCRRequest{
		ImageData: imageData,
		Format:    format,
	})
	if err != nil {
		return "", err
	}
	return resp.Text, nil
}

// AnalyzeStream sends a query to the LLM and streams the response
func (c *Client) AnalyzeStream(ctx context.Context, req *pb.AnalyzeRequest, onChunk func(string)) error {
	stream, err := c.LLM.Analyze(ctx, req)
	if err != nil {
		return err
	}

	for {
		chunk, err := stream.Recv()
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
		if chunk.Content != "" {
			onChunk(chunk.Content)
		}
	}
}

// IsQuestion checks if text is a question
func (c *Client) IsQuestion(ctx context.Context, text string) (bool, error) {
	resp, err := c.LLM.IsQuestion(ctx, &pb.IsQuestionRequest{Text: text})
	if err != nil {
		return false, err
	}
	return resp.IsQuestion, nil
}

// StoreMemory stores text in vector memory
func (c *Client) StoreMemory(ctx context.Context, text, source string) error {
	_, err := c.Memory.Store(ctx, &pb.StoreRequest{
		Text:   text,
		Source: source,
	})
	if err != nil {
		slog.Warn("failed to store memory", "error", err)
	}
	return err
}

// QueryMemory retrieves relevant memories
func (c *Client) QueryMemory(ctx context.Context, query string, n int32) ([]string, error) {
	resp, err := c.Memory.Query(ctx, &pb.QueryRequest{
		QueryText: query,
		NResults:  n,
	})
	if err != nil {
		return nil, err
	}
	return resp.Documents, nil
}
