// Package grpcclient provides a client for the Python inference gRPC server
package grpcclient

import "time"

// Client configuration defaults
const (
	// Keepalive configuration
	DefaultKeepaliveTime    = 10 * time.Second
	DefaultKeepaliveTimeout = 3 * time.Second

	// Health check configuration
	DefaultHealthCheckInterval = 5 * time.Second
	HealthCheckTimeout         = 2 * time.Second
)
