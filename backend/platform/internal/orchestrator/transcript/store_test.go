package transcript

import (
	"strings"
	"testing"
	"time"
)

func TestStoreAdd(t *testing.T) {
	s := NewStore(30, 10)
	s.Add("Hello", "user", "You")

	entries := s.Entries()
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	if entries[0].Text != "Hello" || entries[0].Source != "user" || entries[0].Speaker != "You" {
		t.Errorf("unexpected entry: %+v", entries[0])
	}
}

func TestStoreMaxSize(t *testing.T) {
	s := NewStore(5, 10)
	for i := 0; i < 10; i++ {
		s.Add("msg", "user", "You")
	}

	if len(s.Entries()) != 5 {
		t.Errorf("expected 5 entries, got %d", len(s.Entries()))
	}
}

func TestGetRecent(t *testing.T) {
	s := NewStore(30, 10)
	s.Add("Recent", "user", "You")

	// Manually add an old entry
	s.mu.Lock()
	s.entries = append([]Entry{{
		Timestamp: time.Now().Add(-5 * time.Minute),
		Text:      "Old",
		Source:    "system",
	}}, s.entries...)
	s.mu.Unlock()

	recent := s.GetRecent(60)
	if strings.Contains(recent, "Old") {
		t.Error("should not contain old message")
	}
	if !strings.Contains(recent, "USER: Recent") {
		t.Error("should contain recent message")
	}
}

func TestEmit(t *testing.T) {
	s := NewStore(30, 10)
	go s.Emit(Event{Text: "test", Source: "user"})

	select {
	case e := <-s.Events():
		if e.Text != "test" {
			t.Errorf("expected 'test', got %q", e.Text)
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("timeout waiting for event")
	}
}

func TestEmitNonBlocking(t *testing.T) {
	s := NewStore(30, 1) // Small buffer

	// Fill the buffer
	s.Emit(Event{Text: "1", Source: "user"})

	// This should not block
	done := make(chan struct{})
	go func() {
		s.Emit(Event{Text: "2", Source: "user"})
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(100 * time.Millisecond):
		t.Error("Emit blocked when channel was full")
	}
}

func TestGetUnsummarized(t *testing.T) {
	s := NewStore(30, 10)

	// Add old entries
	now := time.Now()
	s.mu.Lock()
	s.entries = []Entry{
		{Timestamp: now.Add(-3 * time.Minute), Text: "old1", Source: "user"},
		{Timestamp: now.Add(-2 * time.Minute), Text: "old2", Source: "system"},
		{Timestamp: now.Add(-30 * time.Second), Text: "recent", Source: "user"},
	}
	s.mu.Unlock()

	entries, start, end := s.GetUnsummarized(60 * time.Second)
	if len(entries) != 2 {
		t.Errorf("expected 2 unsummarized entries, got %d", len(entries))
	}
	if start.IsZero() || end.IsZero() {
		t.Error("start/end times should not be zero")
	}
}

func TestStoreSummary(t *testing.T) {
	s := NewStore(30, 10)

	start := time.Now().Add(-5 * time.Minute)
	end := time.Now().Add(-2 * time.Minute)
	s.StoreSummary(start, end, "Summary of discussion")

	summaries := s.Summaries()
	if len(summaries) != 1 {
		t.Fatalf("expected 1 summary, got %d", len(summaries))
	}
	if summaries[0].Text != "Summary of discussion" {
		t.Errorf("unexpected summary text: %s", summaries[0].Text)
	}
}

func TestStoreSummaryPrunesOldEntries(t *testing.T) {
	s := NewStore(30, 10)

	// Add entries at different times
	now := time.Now()
	s.mu.Lock()
	s.entries = []Entry{
		{Timestamp: now.Add(-3 * time.Minute), Text: "old1", Source: "user"},
		{Timestamp: now.Add(-2 * time.Minute), Text: "old2", Source: "system"},
		{Timestamp: now.Add(-30 * time.Second), Text: "recent", Source: "user"},
	}
	s.mu.Unlock()

	// Store summary covering old entries
	s.StoreSummary(now.Add(-3*time.Minute), now.Add(-90*time.Second), "Summary")

	entries := s.Entries()
	if len(entries) != 1 {
		t.Errorf("expected 1 entry after pruning, got %d", len(entries))
	}
	if len(entries) > 0 && entries[0].Text != "recent" {
		t.Errorf("expected 'recent' entry to remain, got %q", entries[0].Text)
	}
}

func TestGetRecentWithSummaries(t *testing.T) {
	s := NewStore(30, 10)

	// Add a summary for old content
	now := time.Now()
	s.StoreSummary(now.Add(-10*time.Minute), now.Add(-5*time.Minute), "Previous discussion about X")

	// Add recent entry
	s.Add("Current message", "user", "You")

	recent := s.GetRecent(600) // 10 minutes
	if !strings.Contains(recent, "[Summary]") {
		t.Error("should contain summary marker")
	}
	if !strings.Contains(recent, "Previous discussion") {
		t.Error("should contain summary text")
	}
	if !strings.Contains(recent, "USER: Current message") {
		t.Error("should contain recent raw entry")
	}
}

func TestSummaryPruning(t *testing.T) {
	s := NewStore(30, 10)

	// Add more than 5 summaries
	base := time.Now()
	for i := 0; i < 7; i++ {
		start := base.Add(-time.Duration(10-i) * time.Minute)
		end := start.Add(time.Minute)
		s.StoreSummary(start, end, "summary")
	}

	if len(s.Summaries()) != 5 {
		t.Errorf("expected 5 summaries after pruning, got %d", len(s.Summaries()))
	}
}
