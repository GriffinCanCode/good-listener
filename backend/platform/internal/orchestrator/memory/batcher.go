// Package memory provides batching for memory operations
package memory

import (
	"context"
	"sync"
	"time"

	"github.com/GriffinCanCode/good-listener/backend/platform/internal/grpcclient"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/trace"
)

// Batcher accumulates memory items and flushes them in batches.
type Batcher struct {
	client     *grpcclient.Client
	maxSize    int
	flushDelay time.Duration
	mu         sync.Mutex
	items      []grpcclient.MemoryItem
	timer      *time.Timer
	stopCh     chan struct{}
	wg         sync.WaitGroup
}

// NewBatcher creates a memory batcher.
func NewBatcher(client *grpcclient.Client, maxSize int, flushDelay time.Duration) *Batcher {
	if maxSize <= 0 {
		maxSize = DefaultBatcherMaxSize
	}
	if flushDelay <= 0 {
		flushDelay = DefaultBatcherFlushDelay
	}
	return &Batcher{
		client:     client,
		maxSize:    maxSize,
		flushDelay: flushDelay,
		items:      make([]grpcclient.MemoryItem, 0, maxSize),
		stopCh:     make(chan struct{}),
	}
}

// Add queues an item for batched storage.
func (b *Batcher) Add(text, source string) {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.items = append(b.items, grpcclient.MemoryItem{Text: text, Source: source})

	if len(b.items) >= b.maxSize {
		b.flushLocked()
		return
	}

	// Start or reset timer for delayed flush
	if b.timer == nil {
		b.timer = time.AfterFunc(b.flushDelay, b.timerFlush)
	} else {
		b.timer.Reset(b.flushDelay)
	}
}

func (b *Batcher) timerFlush() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.flushLocked()
}

func (b *Batcher) flushLocked() {
	if len(b.items) == 0 {
		return
	}
	if b.timer != nil {
		b.timer.Stop()
		b.timer = nil
	}
	items := b.items
	b.items = make([]grpcclient.MemoryItem, 0, b.maxSize)

	b.wg.Add(1)
	go func() {
		defer b.wg.Done()
		ctx, span := trace.StartSpan(context.Background(), "memory_batch_flush")
		defer span.End()
		span.SetAttr("count", len(items))

		log := trace.Logger(ctx)
		stored, err := b.client.BatchStoreMemory(ctx, items)
		if err != nil {
			span.SetAttr("error", err.Error())
			log.Warn("batch memory store failed", "error", err, "count", len(items))
		} else {
			log.Debug("batch memory stored", "stored", stored, "submitted", len(items))
		}
	}()
}

// Flush forces immediate flush of pending items.
func (b *Batcher) Flush() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.flushLocked()
}

// Stop stops the batcher and flushes remaining items.
func (b *Batcher) Stop() {
	close(b.stopCh)
	b.Flush()
	b.wg.Wait()
}
