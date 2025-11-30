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
	VADChannelBuffer        = 50

	// Speech processing thresholds
	MinWordsForMemoryStorage = 4

	// Transcript retrieval durations (seconds)
	AutoAnswerTranscriptSeconds = 120
	AnalyzeTranscriptSeconds    = 300

	// Cleanup intervals
	VADCleanupInterval = 5 * time.Minute

	// Summarization configuration
	SummarizationInterval   = 60 * time.Second // Check for summarization every 60s
	SummarizationThreshold  = 90 * time.Second // Summarize entries older than 90s
	SummarizationMinEntries = 3                // Min entries to trigger summarization
	SummarizationMaxLength  = 200              // Target max summary length
	SummarizationTimeout    = 30 * time.Second // Max time for LLM summarization call
)
