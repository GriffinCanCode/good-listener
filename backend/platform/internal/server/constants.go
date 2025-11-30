// Package server provides HTTP and WebSocket handlers
package server

import "time"

// Server configuration constants
const (
	// Text truncation limit for API responses
	TextPreviewLimit = 500

	// Global IP-based rate limiting (prevents multi-connection bypass attacks)
	IPRateLimitMessages        = 30               // Max messages per IP per window
	IPRateLimitWindow          = time.Second      // Sliding window duration
	IPRateLimitCleanupInterval = 5 * time.Minute  // How often to purge stale IP entries
	IPRateLimitEntryTTL        = 10 * time.Minute // TTL for inactive IP entries
)
