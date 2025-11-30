// Package audio handles audio device capture with backpressure
package audio

import (
	"context"
	"encoding/binary"
	"log/slog"
	"math"
	"sync"

	"github.com/gen2brain/malgo"
)

// Chunk represents a captured audio chunk.
type Chunk struct {
	Data      []float32
	DeviceID  string
	Source    string // "user" or "system"
	Timestamp int64
}

// Capturer captures audio from devices with backpressure.
type Capturer struct {
	ctx         *malgo.AllocatedContext
	devices     []*deviceCapture
	outCh       chan Chunk
	sampleRate  uint32
	mu          sync.Mutex
	running     bool
	systemAudio bool
}

type deviceCapture struct {
	device   *malgo.Device
	stopOnce sync.Once
}

// NewCapturer creates a new audio capturer.
func NewCapturer(sampleRate int, bufferSize int, captureSystemAudio bool) (*Capturer, error) {
	ctx, err := malgo.InitContext(nil, malgo.ContextConfig{}, nil)
	if err != nil {
		return nil, err
	}

	return &Capturer{
		ctx:         ctx,
		outCh:       make(chan Chunk, bufferSize),
		sampleRate:  uint32(sampleRate),
		systemAudio: captureSystemAudio,
	}, nil
}

// Output returns the channel for receiving audio chunks.
func (c *Capturer) Output() <-chan Chunk {
	return c.outCh
}

// Start begins capturing audio from available devices.
func (c *Capturer) Start(ctx context.Context) error {
	c.mu.Lock()
	if c.running {
		c.mu.Unlock()
		return nil
	}
	c.running = true
	c.mu.Unlock()

	devices, err := c.ctx.Devices(malgo.Capture)
	if err != nil {
		return err
	}

	for _, info := range devices {
		source := c.classifyDevice(info.Name())
		if source == "" {
			continue
		}
		if source == "system" && !c.systemAudio {
			continue
		}

		if err := c.startDevice(ctx, info, source); err != nil {
			slog.Warn("failed to start device", "device", info.Name(), "error", err)
			continue
		}
		slog.Info("started audio capture", "device", info.Name(), "source", source)
	}

	return nil
}

func (c *Capturer) classifyDevice(name string) string {
	// Check for system audio loopback devices
	systemKeywords := []string{"blackhole", "vb-cable", "loopback", "monitor", "soundflower"}
	for _, kw := range systemKeywords {
		if containsIgnoreCase(name, kw) {
			return "system"
		}
	}

	// Check for microphone
	micKeywords := []string{"microphone", "input", "mic", "built-in"}
	for _, kw := range micKeywords {
		if containsIgnoreCase(name, kw) {
			return "user"
		}
	}

	return ""
}

func (c *Capturer) startDevice(ctx context.Context, info malgo.DeviceInfo, source string) error {
	deviceConfig := malgo.DefaultDeviceConfig(malgo.Capture)
	deviceConfig.Capture.Format = malgo.FormatF32
	deviceConfig.Capture.Channels = 1
	deviceConfig.SampleRate = c.sampleRate
	deviceConfig.Capture.DeviceID = info.ID.Pointer()

	deviceID := info.Name()

	callbacks := malgo.DeviceCallbacks{
		Data: func(_, pSamples []byte, frameCount uint32) {
			samples := bytesToFloat32(pSamples)
			if len(samples) == 0 {
				return
			}

			chunk := Chunk{
				Data:     samples,
				DeviceID: deviceID,
				Source:   source,
			}

			// Non-blocking send with backpressure - drop if channel full
			select {
			case c.outCh <- chunk:
			default:
				slog.Debug("audio buffer full, dropping chunk", "device", deviceID)
			}
		},
	}

	device, err := malgo.InitDevice(c.ctx.Context, deviceConfig, callbacks)
	if err != nil {
		return err
	}

	if err := device.Start(); err != nil {
		device.Uninit()
		return err
	}

	dc := &deviceCapture{device: device}
	c.mu.Lock()
	c.devices = append(c.devices, dc)
	c.mu.Unlock()

	// Stop device when context is canceled.
	go func() {
		<-ctx.Done()
		dc.stop()
	}()

	return nil
}

func (d *deviceCapture) stop() {
	d.stopOnce.Do(func() {
		if d.device.IsStarted() {
			_ = d.device.Stop()
		}
		d.device.Uninit()
	})
}

// Stop stops all audio capture.
func (c *Capturer) Stop() {
	c.mu.Lock()
	defer c.mu.Unlock()

	for _, d := range c.devices {
		d.stop()
	}
	c.devices = nil
	c.running = false
}

// Float32 byte size constant
const float32ByteSize = 4

func bytesToFloat32(b []byte) []float32 {
	if len(b)%float32ByteSize != 0 {
		return nil
	}
	samples := make([]float32, len(b)/float32ByteSize)
	for i := range samples {
		bits := binary.LittleEndian.Uint32(b[i*float32ByteSize:])
		samples[i] = math.Float32frombits(bits)
	}
	return samples
}

func containsIgnoreCase(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || containsIgnoreCaseImpl(s, substr))
}

// ASCII case offset ('a' - 'A')
const asciiCaseOffset = 'a' - 'A'

func containsIgnoreCaseImpl(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		match := true
		for j := 0; j < len(substr); j++ {
			c1, c2 := s[i+j], substr[j]
			if c1 >= 'A' && c1 <= 'Z' {
				c1 += asciiCaseOffset
			}
			if c2 >= 'A' && c2 <= 'Z' {
				c2 += asciiCaseOffset
			}
			if c1 != c2 {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}
