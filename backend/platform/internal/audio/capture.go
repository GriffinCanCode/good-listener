// Package audio handles audio device capture with backpressure
package audio

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/gordonklaus/portaudio"
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
	devices      []*deviceCapture
	outCh        chan Chunk
	sampleRate   int
	framesPerBuf int
	mu           sync.Mutex
	running      bool
	systemAudio  bool
	excludedDevs []string
}

type deviceCapture struct {
	stream   *portaudio.Stream
	cancel   context.CancelFunc
	stopOnce sync.Once
}

// NewCapturer creates a new audio capturer.
func NewCapturer(sampleRate, bufferSize int, captureSystemAudio bool, excludedDevices []string) (*Capturer, error) {
	if err := portaudio.Initialize(); err != nil {
		return nil, err
	}

	return &Capturer{
		outCh:        make(chan Chunk, bufferSize),
		sampleRate:   sampleRate,
		framesPerBuf: 1024, // ~23ms at 44100Hz
		systemAudio:  captureSystemAudio,
		excludedDevs: excludedDevices,
	}, nil
}

// Output returns the channel for receiving audio chunks.
func (c *Capturer) Output() <-chan Chunk { return c.outCh }

// Start begins capturing audio from available devices.
func (c *Capturer) Start(ctx context.Context) error {
	c.mu.Lock()
	if c.running {
		c.mu.Unlock()
		return nil
	}
	c.running = true
	c.mu.Unlock()

	devices, err := portaudio.Devices()
	if err != nil {
		return err
	}

	// Collect candidates by source type, pick best user mic
	var userMic *portaudio.DeviceInfo
	var systemDevs []*portaudio.DeviceInfo

	for _, dev := range devices {
		if dev.MaxInputChannels < 1 || c.isExcluded(dev.Name) {
			continue
		}

		source := c.classifyDevice(dev.Name)
		if source == "" {
			continue
		}

		if source == "system" {
			if c.systemAudio {
				systemDevs = append(systemDevs, dev)
			}
		} else if source == "user" {
			// Prefer built-in/MacBook mic over others
			if userMic == nil || c.preferDevice(dev.Name, userMic.Name) {
				userMic = dev
			}
		}
	}

	// Start single best user mic
	if userMic != nil {
		if err := c.startDevice(ctx, userMic, "user"); err != nil {
			slog.Warn("failed to start device", "device", userMic.Name, "error", err)
		} else {
			slog.Info("started audio capture", "device", userMic.Name, "source", "user")
		}
	}

	// Start system audio devices
	for _, dev := range systemDevs {
		if err := c.startDevice(ctx, dev, "system"); err != nil {
			slog.Warn("failed to start device", "device", dev.Name, "error", err)
			continue
		}
		slog.Info("started audio capture", "device", dev.Name, "source", "system")
	}

	return nil
}

func (c *Capturer) classifyDevice(name string) string {
	systemKeywords := []string{"blackhole", "vb-cable", "loopback", "monitor", "soundflower"}
	for _, kw := range systemKeywords {
		if containsIgnoreCase(name, kw) {
			return "system"
		}
	}

	micKeywords := []string{"microphone", "input", "mic", "built-in"}
	for _, kw := range micKeywords {
		if containsIgnoreCase(name, kw) {
			return "user"
		}
	}

	return ""
}

func (c *Capturer) isExcluded(name string) bool {
	for _, ex := range c.excludedDevs {
		if containsIgnoreCase(name, ex) {
			return true
		}
	}
	return false
}

func (c *Capturer) preferDevice(name, current string) bool {
	// Prefer built-in/MacBook mics over external/virtual
	preferred := []string{"macbook", "built-in"}
	for _, p := range preferred {
		nameHas := containsIgnoreCase(name, p)
		currHas := containsIgnoreCase(current, p)
		if nameHas && !currHas {
			return true
		}
	}
	return false
}

func (c *Capturer) startDevice(ctx context.Context, dev *portaudio.DeviceInfo, source string) error {
	params := portaudio.StreamParameters{
		Input: portaudio.StreamDeviceParameters{
			Device:   dev,
			Channels: 1,
			Latency:  dev.DefaultLowInputLatency,
		},
		SampleRate:      float64(c.sampleRate),
		FramesPerBuffer: c.framesPerBuf,
	}

	buf := make([]float32, c.framesPerBuf)
	stream, err := portaudio.OpenStream(params, buf)
	if err != nil {
		return err
	}

	if err := stream.Start(); err != nil {
		stream.Close()
		return err
	}

	devCtx, cancel := context.WithCancel(ctx)
	dc := &deviceCapture{stream: stream, cancel: cancel}

	c.mu.Lock()
	c.devices = append(c.devices, dc)
	c.mu.Unlock()

	deviceID := dev.Name

	go func() {
		defer dc.stop()
		for {
			select {
			case <-devCtx.Done():
				return
			default:
			}

			if err := stream.Read(); err != nil {
				slog.Debug("audio read error", "device", deviceID, "error", err)
				return
			}

			chunk := Chunk{
				Data:      append([]float32(nil), buf...),
				DeviceID:  deviceID,
				Source:    source,
				Timestamp: time.Now().UnixNano(),
			}

			select {
			case c.outCh <- chunk:
			default:
				slog.Debug("audio buffer full, dropping chunk", "device", deviceID)
			}
		}
	}()

	return nil
}

func (d *deviceCapture) stop() {
	d.stopOnce.Do(func() {
		if d.cancel != nil {
			d.cancel()
		}
		if d.stream != nil {
			_ = d.stream.Stop()
			_ = d.stream.Close()
		}
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
	_ = portaudio.Terminate()
}

func containsIgnoreCase(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || containsIgnoreCaseImpl(s, substr))
}

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
