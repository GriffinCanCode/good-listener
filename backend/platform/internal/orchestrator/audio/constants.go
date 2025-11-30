// Package audio handles audio processing with VAD
package audio

import "time"

// Audio processing constants
const (
	// VAD window size - required by Silero VAD model
	VADWindowSamples = 512

	// Stale state cleanup timeout
	StaleStateTimeout = 5 * time.Minute

	// Float32 byte size for audio conversion
	Float32ByteSize = 4
)
