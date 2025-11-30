// Package screen handles screen capture and OCR processing
package screen

// Screen processing constants
const (
	// Number of stable captures before storing to memory
	StableCountThreshold = 2

	// Minimum text length to store in memory
	MinTextLengthForStorage = 50
)
