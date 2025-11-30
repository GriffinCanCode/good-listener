// Package syncx provides extended synchronization primitives
package syncx

import "sync"

// RWGuard wraps RWMutex with scoped lock helpers that return values.
type RWGuard[T any] struct {
	mu    sync.RWMutex
	value T
}

// NewGuard creates a guarded value.
func NewGuard[T any](initial T) *RWGuard[T] {
	return &RWGuard[T]{value: initial}
}

// Read executes fn while holding read lock, returns result.
func (g *RWGuard[T]) Read(fn func(T) any) any {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return fn(g.value)
}

// Write executes fn while holding write lock, fn receives pointer for mutation.
func (g *RWGuard[T]) Write(fn func(*T)) {
	g.mu.Lock()
	defer g.mu.Unlock()
	fn(&g.value)
}

// Update executes fn while holding write lock, returning a result.
func (g *RWGuard[T]) Update(fn func(*T) any) any {
	g.mu.Lock()
	defer g.mu.Unlock()
	return fn(&g.value)
}

// Get returns a copy of the value (T should be value type or immutable).
func (g *RWGuard[T]) Get() T {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.value
}

// Set atomically replaces the value.
func (g *RWGuard[T]) Set(v T) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.value = v
}

// Swap atomically replaces and returns old value.
func (g *RWGuard[T]) Swap(v T) T {
	g.mu.Lock()
	defer g.mu.Unlock()
	old := g.value
	g.value = v
	return old
}
