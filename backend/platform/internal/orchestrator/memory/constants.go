// Package memory provides batching for memory operations
package memory

import "time"

// Memory batcher defaults
const (
	DefaultBatcherMaxSize    = 50
	DefaultBatcherFlushDelay = 2 * time.Second
)
