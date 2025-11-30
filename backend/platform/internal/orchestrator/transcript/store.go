// Package transcript handles transcript storage and retrieval
package transcript

import (
	"strings"
	"sync"
	"time"
)

// Event represents a transcription event
type Event struct {
	Text   string
	Source string
}

// Entry represents a stored transcript
type Entry struct {
	Timestamp time.Time
	Text      string
	Source    string
}

// Store interface for transcript operations
type Store interface {
	Add(text, source string)
	GetRecent(seconds int) string
	Events() <-chan Event
	Emit(event Event)
}

// MemoryStore implements in-memory transcript storage
type MemoryStore struct {
	mu       sync.RWMutex
	entries  []Entry
	maxSize  int
	eventsCh chan Event
}

// NewStore creates a new transcript store
func NewStore(maxEntries, eventBuffer int) *MemoryStore {
	return &MemoryStore{
		entries:  make([]Entry, 0, maxEntries),
		maxSize:  maxEntries,
		eventsCh: make(chan Event, eventBuffer),
	}
}

// Add stores a new transcript entry
func (s *MemoryStore) Add(text, source string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.entries = append(s.entries, Entry{
		Timestamp: time.Now(),
		Text:      text,
		Source:    source,
	})

	if len(s.entries) > s.maxSize {
		s.entries = s.entries[len(s.entries)-s.maxSize:]
	}
}

// GetRecent returns transcript from last N seconds
func (s *MemoryStore) GetRecent(seconds int) string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	cutoff := time.Now().Add(-time.Duration(seconds) * time.Second)
	var parts []string
	for _, e := range s.entries {
		if e.Timestamp.After(cutoff) {
			parts = append(parts, strings.ToUpper(e.Source)+": "+e.Text)
		}
	}
	return strings.Join(parts, "\n")
}

// Events returns the channel for transcript events
func (s *MemoryStore) Events() <-chan Event {
	return s.eventsCh
}

// Emit sends a transcript event (non-blocking)
func (s *MemoryStore) Emit(event Event) {
	select {
	case s.eventsCh <- event:
	default:
	}
}

// Entries returns a copy of all entries (for testing)
func (s *MemoryStore) Entries() []Entry {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]Entry, len(s.entries))
	copy(result, s.entries)
	return result
}
