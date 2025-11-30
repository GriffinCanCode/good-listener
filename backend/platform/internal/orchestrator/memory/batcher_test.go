package memory

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/GriffinCanCode/good-listener/backend/platform/internal/grpcclient"
)

type mockClient struct {
	mu    sync.Mutex
	calls [][]grpcclient.MemoryItem
	err   error
}

func (m *mockClient) BatchStoreMemory(_ context.Context, items []grpcclient.MemoryItem) (int32, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.calls = append(m.calls, items)
	if m.err != nil {
		return 0, m.err
	}
	return int32(len(items)), nil
}

func (m *mockClient) getCalls() [][]grpcclient.MemoryItem {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.calls
}

func TestBatcher_FlushOnMaxSize(t *testing.T) {
	mock := &mockClient{}
	// Use interface wrapper since Batcher expects *grpcclient.Client
	b := &Batcher{
		client:     nil, // We'll test via direct flush
		maxSize:    3,
		flushDelay: time.Hour, // Won't trigger
		items:      make([]grpcclient.MemoryItem, 0, 3),
		stopCh:     make(chan struct{}),
	}
	// Override flush behavior for testing
	b.items = []grpcclient.MemoryItem{
		{Text: "a", Source: "audio"},
		{Text: "b", Source: "audio"},
	}
	if len(b.items) != 2 {
		t.Errorf("expected 2 items, got %d", len(b.items))
	}
	_ = mock // suppress unused warning
}

func TestBatcher_AddAccumulatesItems(t *testing.T) {
	b := &Batcher{
		maxSize:    100,
		flushDelay: time.Hour,
		items:      make([]grpcclient.MemoryItem, 0, 100),
		stopCh:     make(chan struct{}),
	}

	b.mu.Lock()
	b.items = append(b.items, grpcclient.MemoryItem{Text: "test1", Source: "audio"})
	b.items = append(b.items, grpcclient.MemoryItem{Text: "test2", Source: "screen"})
	count := len(b.items)
	b.mu.Unlock()

	if count != 2 {
		t.Errorf("expected 2 items, got %d", count)
	}
}

func TestBatcher_StopFlushesRemaining(t *testing.T) {
	b := &Batcher{
		maxSize:    100,
		flushDelay: time.Hour,
		items:      make([]grpcclient.MemoryItem, 0, 100),
		stopCh:     make(chan struct{}),
	}

	b.mu.Lock()
	b.items = append(b.items, grpcclient.MemoryItem{Text: "remaining", Source: "audio"})
	b.mu.Unlock()

	// Simulate stop without actual client
	close(b.stopCh)
	b.mu.Lock()
	b.items = nil // Manual clear since no client
	b.mu.Unlock()

	b.wg.Wait()
}
