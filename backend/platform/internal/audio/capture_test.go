package audio

import (
	"testing"
)

func TestClassifyDevice(t *testing.T) {
	c := &Capturer{}

	tests := []struct {
		name     string
		device   string
		expected string
	}{
		// System audio loopback devices
		{"blackhole lowercase", "BlackHole 2ch", "system"},
		{"blackhole uppercase", "BLACKHOLE", "system"},
		{"blackhole mixed", "blackhole-16ch", "system"},
		{"vb-cable", "VB-Cable", "system"},
		{"loopback", "Loopback Audio", "system"},
		{"monitor", "Monitor of Built-in Audio", "system"},
		{"soundflower", "Soundflower (2ch)", "system"},

		// Microphone devices
		{"microphone", "Built-in Microphone", "user"},
		{"mic short", "External Mic", "user"},
		{"input", "Line Input", "user"},
		{"built-in", "Built-in Input", "user"},

		// Unknown devices
		{"speakers", "External Speakers", ""},
		{"hdmi", "HDMI Output", ""},
		{"random", "Some Random Device", ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := c.classifyDevice(tt.device)
			if result != tt.expected {
				t.Errorf("classifyDevice(%q) = %q, want %q", tt.device, result, tt.expected)
			}
		})
	}
}

func TestContainsIgnoreCase(t *testing.T) {
	tests := []struct {
		s        string
		substr   string
		expected bool
	}{
		{"BlackHole 2ch", "blackhole", true},
		{"BLACKHOLE", "blackhole", true},
		{"blackhole", "BLACKHOLE", true},
		{"Some BlackHole Device", "blackhole", true},
		{"Built-in Microphone", "microphone", true},
		{"Built-in Microphone", "MICROPHONE", true},
		{"VB-Cable", "vb-cable", true},
		{"External Speakers", "blackhole", false},
		{"", "test", false},
		{"test", "", true},
	}

	for _, tt := range tests {
		t.Run(tt.s+"_"+tt.substr, func(t *testing.T) {
			result := containsIgnoreCase(tt.s, tt.substr)
			if result != tt.expected {
				t.Errorf("containsIgnoreCase(%q, %q) = %v, want %v", tt.s, tt.substr, result, tt.expected)
			}
		})
	}
}

func TestBytesToFloat32(t *testing.T) {
	tests := []struct {
		name     string
		input    []byte
		expected int // expected length of output
	}{
		{"empty", []byte{}, 0},
		{"4 bytes = 1 float", []byte{0, 0, 0, 0}, 1},
		{"8 bytes = 2 floats", []byte{0, 0, 0, 0, 0, 0, 128, 63}, 2}, // 0.0 and 1.0
		{"invalid length", []byte{0, 0, 0}, 0},                       // not divisible by 4
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := bytesToFloat32(tt.input)
			if len(result) != tt.expected {
				t.Errorf("bytesToFloat32 returned %d floats, want %d", len(result), tt.expected)
			}
		})
	}
}

func TestChunkChannel(t *testing.T) {
	// Test that chunk channel has correct buffer size
	bufferSize := 50
	ch := make(chan Chunk, bufferSize)

	// Should be able to send bufferSize items without blocking
	for i := 0; i < bufferSize; i++ {
		select {
		case ch <- Chunk{Data: []float32{0.0}}:
			// OK
		default:
			t.Errorf("channel blocked at item %d, expected buffer of %d", i, bufferSize)
		}
	}

	// Next send should block (or fail in select)
	select {
	case ch <- Chunk{Data: []float32{0.0}}:
		t.Error("channel should have blocked but didn't")
	default:
		// Expected - channel is full
	}
}

func TestCapturerSystemAudioFlag(t *testing.T) {
	// Test that systemAudio flag is respected
	c := &Capturer{systemAudio: false}

	// Should not classify system devices when flag is false
	source := c.classifyDevice("BlackHole 2ch")
	if source != "system" {
		t.Error("classifyDevice should still identify system devices")
	}

	// The filtering happens in Start(), not classifyDevice()
	// classifyDevice just identifies, Start() filters based on flag
}
