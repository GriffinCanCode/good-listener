// Package transcript handles transcript storage and retrieval with summarization support
package transcript

import (
	"strings"
	"sync"
	"time"
)

// Event represents a transcription event.
type Event struct {
	Text    string
	Source  string
	Speaker string
}

// Entry represents a stored transcript.
type Entry struct {
	Timestamp time.Time
	Text      string
	Source    string
	Speaker   string
}

// Summary represents a compressed transcript segment.
type Summary struct {
	StartTime time.Time
	EndTime   time.Time
	Text      string
}

// Store interface for transcript operations.
type Store interface {
	Add(text, source, speaker string)
	GetRecent(seconds int) string
	GetUnsummarized(olderThan time.Duration) ([]Entry, time.Time, time.Time)
	StoreSummary(start, end time.Time, text string)
	Events() <-chan Event
	Emit(event Event)
}

// MemoryStore implements in-memory transcript storage with summarization.
type MemoryStore struct {
	mu         sync.RWMutex
	entries    []Entry
	summaries  []Summary
	maxSize    int
	eventsCh   chan Event
	summarized time.Time // Entries before this time have been summarized
}

// NewStore creates a new transcript store.
func NewStore(maxEntries, eventBuffer int) *MemoryStore {
	return &MemoryStore{
		entries:  make([]Entry, 0, maxEntries),
		maxSize:  maxEntries,
		eventsCh: make(chan Event, eventBuffer),
	}
}

// Add stores a new transcript entry.
func (s *MemoryStore) Add(text, source, speaker string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.entries = append(s.entries, Entry{
		Timestamp: time.Now(),
		Text:      text,
		Source:    source,
		Speaker:   speaker,
	})

	if len(s.entries) > s.maxSize {
		s.entries = s.entries[len(s.entries)-s.maxSize:]
	}
}

// GetRecent returns transcript from last N seconds (summaries + raw recent text).
func (s *MemoryStore) GetRecent(seconds int) string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	cutoff := time.Now().Add(-time.Duration(seconds) * time.Second)
	var parts []string

	// Add relevant summaries first (older context)
	for _, sum := range s.summaries {
		// Include summary if any part of its range overlaps with window
		if !sum.EndTime.Before(cutoff) {
			parts = append(parts, "[Summary] "+sum.Text)
		}
	}

	// Add raw entries not yet summarized
	for _, e := range s.entries {
		if !e.Timestamp.Before(cutoff) && e.Timestamp.After(s.summarized) {
			parts = append(parts, strings.ToUpper(e.Source)+": "+e.Text)
		}
	}
	return strings.Join(parts, "\n")
}

// GetUnsummarized returns entries older than the threshold that haven't been summarized.
func (s *MemoryStore) GetUnsummarized(olderThan time.Duration) ([]Entry, time.Time, time.Time) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	cutoff := time.Now().Add(-olderThan)
	var result []Entry
	var start, end time.Time

	for _, e := range s.entries {
		if e.Timestamp.Before(cutoff) && e.Timestamp.After(s.summarized) {
			if start.IsZero() || e.Timestamp.Before(start) {
				start = e.Timestamp
			}
			if e.Timestamp.After(end) {
				end = e.Timestamp
			}
			result = append(result, e)
		}
	}
	return result, start, end
}

// StoreSummary stores a summary and marks entries as summarized.
func (s *MemoryStore) StoreSummary(start, end time.Time, text string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.summaries = append(s.summaries, Summary{StartTime: start, EndTime: end, Text: text})
	if end.After(s.summarized) {
		s.summarized = end
	}

	// Prune summarized entries to free memory
	kept := s.entries[:0]
	for _, e := range s.entries {
		if e.Timestamp.After(s.summarized) {
			kept = append(kept, e)
		}
	}
	s.entries = kept

	// Keep only recent summaries (max 5)
	if len(s.summaries) > 5 {
		s.summaries = s.summaries[len(s.summaries)-5:]
	}
}

// Events returns the channel for transcript events.
func (s *MemoryStore) Events() <-chan Event {
	return s.eventsCh
}

// Emit sends a transcript event (non-blocking).
func (s *MemoryStore) Emit(event Event) {
	select {
	case s.eventsCh <- event:
	default:
	}
}

// Entries returns a copy of all entries (for testing).
func (s *MemoryStore) Entries() []Entry {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]Entry, len(s.entries))
	copy(result, s.entries)
	return result
}

// Summaries returns a copy of all summaries (for testing).
func (s *MemoryStore) Summaries() []Summary {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]Summary, len(s.summaries))
	copy(result, s.summaries)
	return result
}
