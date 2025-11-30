// Package trace - HTTP/WebSocket middleware for trace extraction.
package trace

import (
	"encoding/json"
	"net/http"
)

// Middleware extracts or creates trace context for HTTP requests.
func Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tc := extractFromHeaders(r)
		ctx := WithContext(r.Context(), tc)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// extractFromHeaders gets trace context from HTTP headers.
func extractFromHeaders(r *http.Request) Context {
	tc := Context{
		TraceID:      r.Header.Get(TraceIDKey),
		ParentSpanID: r.Header.Get(SpanIDKey),
		SpanID:       generateSpanID(),
	}
	if tc.TraceID == "" {
		tc.TraceID = generateTraceID()
	}
	return tc
}

// ExtractFromJSON extracts trace_id from a JSON message.
// Returns the context and whether a trace_id was found.
func ExtractFromJSON(data []byte) (Context, bool) {
	var msg struct {
		TraceID string `json:"trace_id"`
	}
	if err := json.Unmarshal(data, &msg); err != nil {
		return New(), false
	}
	if msg.TraceID == "" {
		return New(), false
	}
	return Context{
		TraceID: msg.TraceID,
		SpanID:  generateSpanID(),
	}, true
}
