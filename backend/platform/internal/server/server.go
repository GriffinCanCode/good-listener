// Package server provides HTTP and WebSocket handlers
package server

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"

	"github.com/GriffinCanCode/good-listener/backend/platform/internal/config"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/trace"
)

// Message types.
type Message struct {
	Type string `json:"type"`
}

type ChatMessage struct {
	Type    string `json:"type"`
	Message string `json:"message"`
	TraceID string `json:"trace_id,omitempty"`
}

type TranscriptMessage struct {
	Type   string `json:"type"`
	Text   string `json:"text"`
	Source string `json:"source"`
}

type ChunkMessage struct {
	Type    string `json:"type"`
	Content string `json:"content"`
}

type StartMessage struct {
	Type string `json:"type"`
	Role string `json:"role"`
}

type DoneMessage struct {
	Type string `json:"type"`
}

type AutoStartMessage struct {
	Type     string `json:"type"`
	Question string `json:"question"`
}

type AutoChunkMessage struct {
	Type    string `json:"type"`
	Content string `json:"content"`
}

type AutoDoneMessage struct {
	Type string `json:"type"`
}

type RateLimitedMessage struct {
	Type    string `json:"type"`
	Message string `json:"message"`
}

// rateLimiter tracks message timestamps using a sliding window.
type rateLimiter struct {
	timestamps []time.Time
	mu         sync.Mutex
}

// allow checks if a message is allowed and records the timestamp if so.
func (r *rateLimiter) allow() bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now()
	cutoff := now.Add(-RateLimitWindow)

	// Prune old timestamps
	valid := r.timestamps[:0]
	for _, t := range r.timestamps {
		if t.After(cutoff) {
			valid = append(valid, t)
		}
	}
	r.timestamps = valid

	if len(r.timestamps) >= RateLimitMessages {
		return false
	}

	r.timestamps = append(r.timestamps, now)
	return true
}

// Server handles HTTP and WebSocket connections.
type Server struct {
	orch       *orchestrator.Orchestrator
	mu         sync.RWMutex
	conns      map[*websocket.Conn]struct{}
	rateLimits map[*websocket.Conn]*rateLimiter
}

// New creates a new server.
func New(orch *orchestrator.Orchestrator, _ *config.Config) *Server {
	s := &Server{
		orch:       orch,
		conns:      make(map[*websocket.Conn]struct{}),
		rateLimits: make(map[*websocket.Conn]*rateLimiter),
	}

	// Start broadcasters
	go s.broadcastTranscripts()
	go s.broadcastAutoAnswers()

	return s
}

// Handler returns the HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	// WebSocket endpoint
	mux.HandleFunc("/ws", s.handleWebSocket)

	// REST API
	mux.HandleFunc("GET /api/capture", s.handleCapture)
	mux.HandleFunc("POST /api/recording/start", s.handleRecordingStart)
	mux.HandleFunc("POST /api/recording/stop", s.handleRecordingStop)

	// Apply middleware: trace -> CORS
	return corsMiddleware(trace.Middleware(mux))
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "*")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func (s *Server) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := websocket.Accept(w, r, &websocket.AcceptOptions{
		OriginPatterns: []string{"*"},
	})
	if err != nil {
		slog.Error("websocket accept error", "error", err)
		return
	}
	defer func() { _ = conn.Close(websocket.StatusNormalClosure, "") }()

	s.mu.Lock()
	s.conns[conn] = struct{}{}
	s.rateLimits[conn] = &rateLimiter{}
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		delete(s.conns, conn)
		delete(s.rateLimits, conn)
		s.mu.Unlock()
	}()

	// Get trace context from HTTP upgrade request
	baseCtx := r.Context()
	log := trace.Logger(baseCtx)
	log.Info("websocket connected", "remote", r.RemoteAddr)

	for {
		var msg json.RawMessage
		if err := wsjson.Read(baseCtx, conn, &msg); err != nil {
			log.Debug("websocket read error", "error", err)
			return
		}

		// Check rate limit
		s.mu.RLock()
		rl := s.rateLimits[conn]
		s.mu.RUnlock()

		if !rl.allow() {
			log.Warn("rate limit exceeded", "remote", r.RemoteAddr)
			_ = wsjson.Write(baseCtx, conn, RateLimitedMessage{
				Type:    "error",
				Message: "rate limit exceeded",
			})
			continue
		}

		var base Message
		if err := json.Unmarshal(msg, &base); err != nil {
			continue
		}

		switch base.Type {
		case "chat":
			var chat ChatMessage
			if err := json.Unmarshal(msg, &chat); err != nil {
				continue
			}
			// Extract trace_id from message or create new trace context
			ctx := baseCtx
			if chat.TraceID != "" {
				tc := trace.Context{TraceID: chat.TraceID, SpanID: ""}
				tc = trace.NewChild(tc)
				ctx = trace.WithContext(ctx, tc)
			} else {
				ctx, _ = trace.EnsureContext(ctx)
			}
			s.handleChat(ctx, conn, chat.Message)
		}
	}
}

func (s *Server) handleChat(ctx context.Context, conn *websocket.Conn, query string) {
	ctx, span := trace.StartSpan(ctx, "handle_chat")
	defer span.End()

	log := trace.Logger(ctx)
	log.Info("chat message", "query", query)

	// Send start
	_ = wsjson.Write(ctx, conn, StartMessage{Type: "start", Role: "assistant"})

	// Stream LLM response
	err := s.orch.Analyze(ctx, query, func(chunk string) {
		_ = wsjson.Write(ctx, conn, ChunkMessage{Type: "chunk", Content: chunk})
	})

	if err != nil {
		span.SetAttr("error", err.Error())
		log.Error("analyze error", "error", err)
		_ = wsjson.Write(ctx, conn, ChunkMessage{Type: "chunk", Content: "Error: " + err.Error()})
	}

	// Send done
	_ = wsjson.Write(ctx, conn, DoneMessage{Type: "done"})
}

func (s *Server) broadcastTranscripts() {
	for evt := range s.orch.TranscriptEvents() {
		msg := TranscriptMessage{
			Type:    "transcript",
			Text:    evt.Text,
			Source:  evt.Source,
			Speaker: evt.Speaker,
		}

		s.mu.RLock()
		for conn := range s.conns {
			go func(c *websocket.Conn) {
				ctx := context.Background()
				_ = wsjson.Write(ctx, c, msg)
			}(conn)
		}
		s.mu.RUnlock()
	}
}

func (s *Server) broadcastAutoAnswers() {
	for evt := range s.orch.AutoAnswerEvents() {
		var msg interface{}
		switch evt.Type {
		case "start":
			msg = AutoStartMessage{Type: "auto_start", Question: evt.Question}
		case "chunk":
			msg = AutoChunkMessage{Type: "auto_chunk", Content: evt.Content}
		case "done":
			msg = AutoDoneMessage{Type: "auto_done"}
		default:
			continue
		}

		s.mu.RLock()
		for conn := range s.conns {
			go func(c *websocket.Conn, m interface{}) {
				_ = wsjson.Write(context.Background(), c, m)
			}(conn, msg)
		}
		s.mu.RUnlock()
	}
}

func (s *Server) handleCapture(w http.ResponseWriter, r *http.Request) {
	text := s.orch.GetLatestScreenText()
	if len(text) > TextPreviewLimit {
		text = text[:TextPreviewLimit] + "..."
	}

	json.NewEncoder(w).Encode(map[string]string{
		"message":        "Screen processed",
		"extracted_text": text,
	})
}

func (s *Server) handleRecordingStart(w http.ResponseWriter, r *http.Request) {
	s.orch.SetRecording(true)
	json.NewEncoder(w).Encode(map[string]string{"status": "recording_started"})
}

func (s *Server) handleRecordingStop(w http.ResponseWriter, r *http.Request) {
	s.orch.SetRecording(false)
	json.NewEncoder(w).Encode(map[string]string{"status": "recording_stopped"})
}
