package pb

import (
	"testing"
)

func TestBoundingBox(t *testing.T) {
	box := &BoundingBox{
		X1:         10,
		Y1:         20,
		X2:         100,
		Y2:         50,
		Text:       "Hello",
		Confidence: 0.95,
	}

	if box.X1 != 10 || box.Y1 != 20 || box.X2 != 100 || box.Y2 != 50 {
		t.Error("bounding box coordinates incorrect")
	}
	if box.Text != "Hello" {
		t.Errorf("Text = %q, want %q", box.Text, "Hello")
	}
	if box.Confidence != 0.95 {
		t.Errorf("Confidence = %f, want %f", box.Confidence, 0.95)
	}
}

func TestAudioChunk(t *testing.T) {
	chunk := &AudioChunk{
		Data:        []byte{0, 0, 0, 0},
		TimestampNs: 1234567890,
		DeviceId:    "device-1",
	}

	if len(chunk.Data) != 4 {
		t.Errorf("Data length = %d, want 4", len(chunk.Data))
	}
	if chunk.TimestampNs != 1234567890 {
		t.Errorf("TimestampNs = %d, want %d", chunk.TimestampNs, 1234567890)
	}
	if chunk.DeviceId != "device-1" {
		t.Errorf("DeviceId = %q, want %q", chunk.DeviceId, "device-1")
	}
}

func TestTranscriptSegment(t *testing.T) {
	segment := &TranscriptSegment{
		Text:     "Hello world",
		DeviceId: "mic-1",
		StartNs:  1000000,
		EndNs:    2000000,
		IsFinal:  true,
	}

	if segment.Text != "Hello world" {
		t.Errorf("Text = %q, want %q", segment.Text, "Hello world")
	}
	if !segment.IsFinal {
		t.Error("IsFinal should be true")
	}
	if segment.EndNs <= segment.StartNs {
		t.Error("EndNs should be greater than StartNs")
	}
}

func TestResetStateRequest(t *testing.T) {
	req := &ResetStateRequest{}
	// Just verify it can be created
	if req == nil {
		t.Error("ResetStateRequest should not be nil")
	}
}

func TestResetStateResponse(t *testing.T) {
	resp := &ResetStateResponse{Success: true}
	if !resp.Success {
		t.Error("Success should be true")
	}
}

func TestClearRequest(t *testing.T) {
	req := &ClearRequest{}
	if req == nil {
		t.Error("ClearRequest should not be nil")
	}
}

func TestClearResponse(t *testing.T) {
	resp := &ClearResponse{DeletedCount: 100}
	if resp.DeletedCount != 100 {
		t.Errorf("DeletedCount = %d, want %d", resp.DeletedCount, 100)
	}
}

func TestStoreResponse(t *testing.T) {
	resp := &StoreResponse{
		Id:      "memory-123",
		Success: true,
	}

	if resp.Id != "memory-123" {
		t.Errorf("Id = %q, want %q", resp.Id, "memory-123")
	}
	if !resp.Success {
		t.Error("Success should be true")
	}
}
