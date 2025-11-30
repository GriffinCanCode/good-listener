// Package orchestrator coordinates audio, screen, and inference services
package orchestrator

import "time"

// Orchestrator configuration constants
const (
	// Audio capture buffer size
	AudioBufferSize = 100

	// Transcript store configuration
	TranscriptMaxEntries  = 30
	TranscriptEventBuffer = 100

	// Memory batcher configuration
	MemoryBatcherMaxSize    = 50
	MemoryBatcherFlushDelay = 2 * time.Second

	// Channel buffer sizes
	AutoAnswerChannelBuffer = 10

	// Speech processing thresholds
	MinWordsForMemoryStorage = 4

	// Transcript retrieval durations (seconds)
	AutoAnswerTranscriptSeconds = 120
	AnalyzeTranscriptSeconds    = 300

	// Cleanup intervals
	VADCleanupInterval = 5 * time.Minute
)
