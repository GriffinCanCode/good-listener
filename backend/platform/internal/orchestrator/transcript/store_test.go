package transcript

import (
	"strings"
	"testing"
	"time"
)

func TestStoreAdd(t *testing.T) {
	s := NewStore(30, 10)
	s.Add("Hello", "user")

	entries := s.Entries()
	if len(entries) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(entries))
	}
	if entries[0].Text != "Hello" || entries[0].Source != "user" {
		t.Errorf("unexpected entry: %+v", entries[0])
	}
}

func TestStoreMaxSize(t *testing.T) {
	s := NewStore(5, 10)
	for i := 0; i < 10; i++ {
		s.Add("msg", "user")
	}

	if len(s.Entries()) != 5 {
		t.Errorf("expected 5 entries, got %d", len(s.Entries()))
	}
}

func TestGetRecent(t *testing.T) {
	s := NewStore(30, 10)
	s.Add("Recent", "user")

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
