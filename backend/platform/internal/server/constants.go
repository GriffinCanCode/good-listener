// Package server provides HTTP and WebSocket handlers
package server

import "time"

// Server configuration constants
const (
	// Text truncation limit for API responses
	TextPreviewLimit = 500

	// Rate limiting
	RateLimitMessages = 10          // Max messages per window
	RateLimitWindow   = time.Second // Sliding window duration
)
