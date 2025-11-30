// Package screen handles screen capture and OCR processing
package screen

// Screen processing constants
const (
	// Number of stable captures before storing to memory
	StableCountThreshold = 2

	// Minimum text length to store in memory
	MinTextLengthForStorage = 50

	// PHashSimilarityThreshold is the minimum similarity (0-1) to skip OCR.
	// 95% similarity means Hamming distance <= 3 bits on a 64-bit hash.
	PHashSimilarityThreshold = 0.95

	// MaxHashDistance is max Hamming distance to skip OCR (derived from threshold).
	// 64-bit hash * (1 - 0.95) = 3.2, so we use 3.
	MaxHashDistance = 3
)
