// Package grpcclient provides a client for the Python inference gRPC server
package grpcclient

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"time"

	"github.com/good-listener/platform/internal/resilience"
	"github.com/good-listener/platform/internal/trace"
	pb "github.com/good-listener/platform/pkg/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/status"
)

// Re-export for backwards compatibility
var (
	ErrCircuitOpen = resilience.ErrOpen
	ErrServerDown  = errors.New("inference server unavailable")
)

// CircuitState type alias for backwards compatibility
type CircuitState = resilience.State

const (
	CircuitClosed   = resilience.Closed
	CircuitOpen     = resilience.Open
	CircuitHalfOpen = resilience.HalfOpen
)

// ClientConfig holds client configuration
type ClientConfig struct {
	KeepaliveTime       time.Duration
	KeepaliveTimeout    time.Duration
	HealthCheckInterval time.Duration
	BreakerConfig       resilience.Config
}

// DefaultConfig returns production-ready defaults
func DefaultConfig() ClientConfig {
	return ClientConfig{
		KeepaliveTime:       10 * time.Second,
		KeepaliveTimeout:    3 * time.Second,
		HealthCheckInterval: 5 * time.Second,
		BreakerConfig:       resilience.DefaultConfig(),
	}
}

// Client wraps all inference service clients
type Client struct {
	conn          *grpc.ClientConn
	Transcription pb.TranscriptionServiceClient
	VAD           pb.VADServiceClient
	OCR           pb.OCRServiceClient
	LLM           pb.LLMServiceClient
	Memory        pb.MemoryServiceClient
	Health        grpc_health_v1.HealthClient
	cb            *resilience.Breaker
	healthCancel  context.CancelFunc
}

// New creates a new inference client with default config
func New(addr string) (*Client, error) {
	return NewWithConfig(addr, DefaultConfig())
}

// NewWithConfig creates a client with custom configuration
func NewWithConfig(addr string, cfg ClientConfig) (*Client, error) {
	conn, err := grpc.Dial(addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                cfg.KeepaliveTime,
			Timeout:             cfg.KeepaliveTimeout,
			PermitWithoutStream: true,
		}),
		grpc.WithDefaultServiceConfig(`{"healthCheckConfig":{"serviceName":""}}`),
		grpc.WithUnaryInterceptor(trace.UnaryClientInterceptor()),
		grpc.WithStreamInterceptor(trace.StreamClientInterceptor()),
	)
	if err != nil {
		return nil, err
	}

	c := &Client{
		conn:          conn,
		Transcription: pb.NewTranscriptionServiceClient(conn),
		VAD:           pb.NewVADServiceClient(conn),
		OCR:           pb.NewOCRServiceClient(conn),
		LLM:           pb.NewLLMServiceClient(conn),
		Memory:        pb.NewMemoryServiceClient(conn),
		Health:        grpc_health_v1.NewHealthClient(conn),
		cb:            resilience.New(cfg.BreakerConfig),
	}

	ctx, cancel := context.WithCancel(context.Background())
	c.healthCancel = cancel
	go c.monitorHealth(ctx, cfg.HealthCheckInterval)

	return c, nil
}

// monitorHealth periodically checks server health
func (c *Client) monitorHealth(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := c.checkHealth(ctx); err != nil {
				slog.Debug("health check failed", "error", err)
			}
		}
	}
}

// checkHealth performs a health check
func (c *Client) checkHealth(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()

	resp, err := c.Health.Check(ctx, &grpc_health_v1.HealthCheckRequest{})
	if err != nil {
		c.cb.Failure()
		return err
	}
	if resp.Status != grpc_health_v1.HealthCheckResponse_SERVING {
		c.cb.Failure()
		return ErrServerDown
	}
	c.cb.Success()
	return nil
}

// CheckHealth performs an on-demand health check
func (c *Client) CheckHealth(ctx context.Context) (bool, error) {
	if err := c.cb.Allow(); err != nil {
		return false, err
	}
	if err := c.checkHealth(ctx); err != nil {
		return false, err
	}
	return true, nil
}

// IsConnected returns true if connection is ready
func (c *Client) IsConnected() bool {
	return c.conn.GetState() == connectivity.Ready
}

// CircuitState returns current circuit breaker state
func (c *Client) CircuitState() CircuitState {
	return c.cb.State()
}

// Breaker returns the underlying circuit breaker for advanced use
func (c *Client) Breaker() *resilience.Breaker {
	return c.cb
}

// withBreaker wraps a call with circuit breaker logic
func (c *Client) withBreaker(fn func() error) error {
	if err := c.cb.Allow(); err != nil {
		return err
	}
	err := fn()
	if err != nil && isTransient(err) {
		c.cb.Failure()
	} else if err == nil {
		c.cb.Success()
	}
	return err
}

// isTransient checks if error should trip circuit breaker
func isTransient(err error) bool {
	s, ok := status.FromError(err)
	if !ok {
		return true
	}
	switch s.Code() {
	case codes.Unavailable, codes.DeadlineExceeded, codes.ResourceExhausted:
		return true
	default:
		return false
	}
}

// Close closes the gRPC connection and stops health monitoring
func (c *Client) Close() error {
	if c.healthCancel != nil {
		c.healthCancel()
	}
	return c.conn.Close()
}

// Transcribe sends audio for transcription
func (c *Client) Transcribe(ctx context.Context, audio []byte, sampleRate int32) (string, error) {
	var result string
	err := c.withBreaker(func() error {
		resp, err := c.Transcription.Transcribe(ctx, &pb.TranscribeRequest{
			AudioData:  audio,
			SampleRate: sampleRate,
		})
		if err != nil {
			return err
		}
		result = resp.Text
		return nil
	})
	return result, err
}

// DetectSpeech checks if audio chunk contains speech
func (c *Client) DetectSpeech(ctx context.Context, audio []byte, sampleRate int32) (float32, bool, error) {
	var prob float32
	var isSpeech bool
	err := c.withBreaker(func() error {
		resp, err := c.VAD.DetectSpeech(ctx, &pb.VADRequest{
			AudioChunk: audio,
			SampleRate: sampleRate,
		})
		if err != nil {
			return err
		}
		prob, isSpeech = resp.SpeechProbability, resp.IsSpeech
		return nil
	})
	return prob, isSpeech, err
}

// ResetVAD resets VAD model state
func (c *Client) ResetVAD(ctx context.Context) error {
	return c.withBreaker(func() error {
		_, err := c.VAD.ResetState(ctx, &pb.ResetStateRequest{})
		return err
	})
}

// ExtractText performs OCR on an image
func (c *Client) ExtractText(ctx context.Context, imageData []byte, format string) (string, error) {
	var result string
	err := c.withBreaker(func() error {
		resp, err := c.OCR.ExtractText(ctx, &pb.OCRRequest{
			ImageData: imageData,
			Format:    format,
		})
		if err != nil {
			return err
		}
		result = resp.Text
		return nil
	})
	return result, err
}

// AnalyzeStream sends a query to the LLM and streams the response
func (c *Client) AnalyzeStream(ctx context.Context, req *pb.AnalyzeRequest, onChunk func(string)) error {
	if err := c.cb.Allow(); err != nil {
		return err
	}

	stream, err := c.LLM.Analyze(ctx, req)
	if err != nil {
		if isTransient(err) {
			c.cb.Failure()
		}
		return err
	}

	for {
		chunk, err := stream.Recv()
		if err == io.EOF {
			c.cb.Success()
			return nil
		}
		if err != nil {
			if isTransient(err) {
				c.cb.Failure()
			}
			return err
		}
		if chunk.Content != "" {
			onChunk(chunk.Content)
		}
	}
}

// IsQuestion checks if text is a question
func (c *Client) IsQuestion(ctx context.Context, text string) (bool, error) {
	var result bool
	err := c.withBreaker(func() error {
		resp, err := c.LLM.IsQuestion(ctx, &pb.IsQuestionRequest{Text: text})
		if err != nil {
			return err
		}
		result = resp.IsQuestion
		return nil
	})
	return result, err
}

// StoreMemory stores text in vector memory
func (c *Client) StoreMemory(ctx context.Context, text, source string) error {
	err := c.withBreaker(func() error {
		_, err := c.Memory.Store(ctx, &pb.StoreRequest{
			Text:   text,
			Source: source,
		})
		return err
	})
	if err != nil {
		slog.Warn("failed to store memory", "error", err)
	}
	return err
}

// QueryMemory retrieves relevant memories
func (c *Client) QueryMemory(ctx context.Context, query string, n int32) ([]string, error) {
	var result []string
	err := c.withBreaker(func() error {
		resp, err := c.Memory.Query(ctx, &pb.QueryRequest{
			QueryText: query,
			NResults:  n,
		})
		if err != nil {
			return err
		}
		result = resp.Documents
		return nil
	})
	return result, err
}
