package syncx

import (
	"sync"
	"testing"
)

func TestGuardGetSet(t *testing.T) {
	g := NewGuard(42)

	if got := g.Get(); got != 42 {
		t.Errorf("Get() = %d, want 42", got)
	}

	g.Set(100)
	if got := g.Get(); got != 100 {
		t.Errorf("Get() after Set = %d, want 100", got)
	}
}

func TestGuardSwap(t *testing.T) {
	g := NewGuard("hello")

	old := g.Swap("world")
	if old != "hello" {
		t.Errorf("Swap returned %q, want %q", old, "hello")
	}
	if got := g.Get(); got != "world" {
		t.Errorf("Get() after Swap = %q, want %q", got, "world")
	}
}

func TestGuardRead(t *testing.T) {
	g := NewGuard([]int{1, 2, 3})

	result := g.Read(func(v []int) any {
		return len(v)
	})

	if result != 3 {
		t.Errorf("Read() = %v, want 3", result)
	}
}

func TestGuardWrite(t *testing.T) {
	type counter struct{ value int }
	g := NewGuard(counter{value: 0})

	g.Write(func(c *counter) {
		c.value = 42
	})

	if got := g.Get().value; got != 42 {
		t.Errorf("Get().value = %d, want 42", got)
	}
}

func TestGuardUpdate(t *testing.T) {
	g := NewGuard(10)

	result := g.Update(func(v *int) any {
		old := *v
		*v = 20
		return old
	})

	if result != 10 {
		t.Errorf("Update returned %v, want 10", result)
	}
	if got := g.Get(); got != 20 {
		t.Errorf("Get() = %d, want 20", got)
	}
}

func TestGuardConcurrentSafety(t *testing.T) {
	g := NewGuard(0)
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			g.Write(func(v *int) {
				*v++
			})
		}()
	}

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_ = g.Get()
		}()
	}

	wg.Wait()

	if got := g.Get(); got != 100 {
		t.Errorf("Get() = %d, want 100", got)
	}
}

func TestGuardWithStruct(t *testing.T) {
	type state struct {
		failures  int
		successes int
	}

	g := NewGuard(state{})

	g.Write(func(s *state) {
		s.failures = 5
		s.successes = 10
	})

	got := g.Get()
	if got.failures != 5 || got.successes != 10 {
		t.Errorf("Get() = %+v, want {5, 10}", got)
	}
}
