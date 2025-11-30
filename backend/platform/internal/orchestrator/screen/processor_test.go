package screen

import (
	"context"
	"testing"
)

type mockCapturer struct {
	img     []byte
	changed bool
}

func (m *mockCapturer) Capture() ([]byte, bool) { return m.img, m.changed }
func (m *mockCapturer) CaptureAlways() []byte   { return m.img }
func (m *mockCapturer) Close()                  {}

type mockOCR struct {
	text string
	err  error
}

func (m *mockOCR) ExtractText(_ context.Context, _ []byte, _ string) (string, error) {
	return m.text, m.err
}

type mockMemory struct {
	stored []string
}

func (m *mockMemory) StoreMemory(_ context.Context, text, _ string) error {
	m.stored = append(m.stored, text)
	return nil
}

func TestProcessorText(t *testing.T) {
	p := &Processor{text: "Screen content"}

	if p.Text() != "Screen content" {
		t.Errorf("Text() = %q, want %q", p.Text(), "Screen content")
	}
}

func TestProcessorImage(t *testing.T) {
	img := []byte{0xFF, 0xD8, 0xFF, 0xE0}
	p := &Processor{image: img}

	if len(p.Image()) != len(img) {
		t.Errorf("Image() length = %d, want %d", len(p.Image()), len(img))
	}
}

func TestProcessorSetRecording(t *testing.T) {
	p := &Processor{recording: true}

	p.SetRecording(false)
	if p.recording {
		t.Error("recording should be false")
	}

	p.SetRecording(true)
	if !p.recording {
		t.Error("recording should be true")
	}
}

func TestNewProcessor(t *testing.T) {
	cap := &mockCapturer{}
	ocr := &mockOCR{}
	mem := &mockMemory{}

	p := NewProcessor(cap, ocr, mem)

	if p == nil {
		t.Fatal("expected processor, got nil")
	}
	if !p.recording {
		t.Error("recording should be true by default")
	}
}
