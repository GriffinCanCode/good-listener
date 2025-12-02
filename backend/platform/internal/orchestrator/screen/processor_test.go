package screen

import (
	"bytes"
	"context"
	"image"
	"image/color"
	"image/jpeg"
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

	p := NewProcessor(cap, ocr)

	if p == nil {
		t.Fatal("expected processor, got nil")
	}
	if !p.recording {
		t.Error("recording should be true by default")
	}
}

// makePatternJPEG creates test images with distinct patterns for pHash testing.
func makePatternJPEG(pattern int) []byte {
	img := image.NewRGBA(image.Rect(0, 0, 64, 64))
	for y := 0; y < 64; y++ {
		for x := 0; x < 64; x++ {
			var c color.RGBA
			switch pattern {
			case 0: // solid gray
				c = color.RGBA{R: 128, G: 128, B: 128, A: 255}
			case 1: // checkerboard - visually distinct
				if (x/8+y/8)%2 == 0 {
					c = color.RGBA{R: 255, G: 255, B: 255, A: 255}
				} else {
					c = color.RGBA{R: 0, G: 0, B: 0, A: 255}
				}
			case 2: // horizontal gradient - different frequency content
				c = color.RGBA{R: uint8(x * 4), G: 0, B: uint8(255 - x*4), A: 255}
			}
			img.Set(x, y, c)
		}
	}
	var buf bytes.Buffer
	_ = jpeg.Encode(&buf, img, nil)
	return buf.Bytes()
}

func TestShouldSkipOCR_FirstFrame(t *testing.T) {
	p := &Processor{}
	img := makePatternJPEG(0)

	if p.shouldSkipOCR(img) {
		t.Error("first frame should not skip OCR")
	}
	if p.lastHash == nil {
		t.Error("lastHash should be set after first frame")
	}
}

func TestShouldSkipOCR_IdenticalFrames(t *testing.T) {
	p := &Processor{}
	img := makePatternJPEG(0)

	p.shouldSkipOCR(img)
	if !p.shouldSkipOCR(img) {
		t.Error("identical frames should skip OCR")
	}
}

func TestShouldSkipOCR_DifferentFrames(t *testing.T) {
	p := &Processor{}
	img1 := makePatternJPEG(1) // checkerboard
	img2 := makePatternJPEG(2) // horizontal gradient

	p.shouldSkipOCR(img1)
	if p.shouldSkipOCR(img2) {
		t.Error("visually distinct frames should not skip OCR")
	}
}
