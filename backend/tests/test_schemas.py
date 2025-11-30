"""Tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError


class TestWebSocketPayloads:
    """Tests for WebSocket message schemas."""

    def test_transcript_payload(self):
        """TranscriptPayload validates correctly."""
        from app.core.schemas import TranscriptPayload
        
        payload = TranscriptPayload(text="Hello world", source="user")
        
        assert payload.type == "transcript"
        assert payload.text == "Hello world"
        assert payload.source == "user"
        assert payload.model_dump_json()

    def test_chunk_payload(self):
        """ChunkPayload validates correctly."""
        from app.core.schemas import ChunkPayload
        
        payload = ChunkPayload(content="Response chunk")
        
        assert payload.type == "chunk"
        assert payload.content == "Response chunk"

    def test_start_payload(self):
        """StartPayload has default values."""
        from app.core.schemas import StartPayload
        
        payload = StartPayload()
        
        assert payload.type == "start"
        assert payload.role == "assistant"

    def test_done_payload(self):
        """DonePayload validates correctly."""
        from app.core.schemas import DonePayload
        
        payload = DonePayload()
        
        assert payload.type == "done"

    def test_auto_answer_payload(self):
        """AutoAnswerPayload validates correctly."""
        from app.core.schemas import AutoAnswerPayload
        
        payload = AutoAnswerPayload(question="What is X?", content="X is...")
        
        assert payload.type == "auto_answer"
        assert payload.question == "What is X?"
        assert payload.content == "X is..."

    def test_auto_answer_chunk_payload(self):
        """AutoAnswerChunkPayload validates correctly."""
        from app.core.schemas import AutoAnswerChunkPayload
        
        payload = AutoAnswerChunkPayload(question="Question?", content="chunk")
        
        assert payload.type == "auto_chunk"

    def test_auto_answer_start_payload(self):
        """AutoAnswerStartPayload validates correctly."""
        from app.core.schemas import AutoAnswerStartPayload
        
        payload = AutoAnswerStartPayload(question="Question?")
        
        assert payload.type == "auto_start"
        assert payload.question == "Question?"

    def test_auto_answer_done_payload(self):
        """AutoAnswerDonePayload validates correctly."""
        from app.core.schemas import AutoAnswerDonePayload
        
        payload = AutoAnswerDonePayload(question="Question?")
        
        assert payload.type == "auto_done"


class TestChatRequest:
    """Tests for chat request schema."""

    def test_chat_request_valid(self):
        """ChatRequest validates with message."""
        from app.core.schemas import ChatRequest
        
        request = ChatRequest(message="Hello AI")
        
        assert request.type == "chat"
        assert request.message == "Hello AI"

    def test_chat_request_missing_message(self):
        """ChatRequest requires message field."""
        from app.core.schemas import ChatRequest
        
        with pytest.raises(ValidationError):
            ChatRequest()

    def test_chat_request_from_dict(self):
        """ChatRequest can be created from dict."""
        from app.core.schemas import ChatRequest
        
        data = {"type": "chat", "message": "Test message"}
        request = ChatRequest(**data)
        
        assert request.message == "Test message"


class TestResponseSchemas:
    """Tests for API response schemas."""

    def test_capture_response(self):
        """CaptureResponse validates correctly."""
        from app.core.schemas import CaptureResponse
        
        response = CaptureResponse(
            message="Screen processed",
            extracted_text="Hello World"
        )
        
        assert response.message == "Screen processed"
        assert response.extracted_text == "Hello World"

    def test_capture_response_missing_fields(self):
        """CaptureResponse requires all fields."""
        from app.core.schemas import CaptureResponse
        
        with pytest.raises(ValidationError):
            CaptureResponse(message="Only message")

    def test_recording_status_response(self):
        """RecordingStatusResponse validates correctly."""
        from app.core.schemas import RecordingStatusResponse
        
        response = RecordingStatusResponse(status="recording_started")
        
        assert response.status == "recording_started"


class TestPayloadSerialization:
    """Tests for JSON serialization."""

    def test_transcript_payload_json(self):
        """TranscriptPayload serializes to JSON."""
        from app.core.schemas import TranscriptPayload
        import json
        
        payload = TranscriptPayload(text="Test", source="system")
        json_str = payload.model_dump_json()
        
        parsed = json.loads(json_str)
        assert parsed["type"] == "transcript"
        assert parsed["text"] == "Test"
        assert parsed["source"] == "system"

    def test_chunk_payload_json(self):
        """ChunkPayload serializes to JSON."""
        from app.core.schemas import ChunkPayload
        import json
        
        payload = ChunkPayload(content="Response")
        json_str = payload.model_dump_json()
        
        parsed = json.loads(json_str)
        assert parsed["type"] == "chunk"
        assert parsed["content"] == "Response"

    def test_payload_model_dump(self):
        """Payloads can be dumped to dict."""
        from app.core.schemas import StartPayload
        
        payload = StartPayload()
        data = payload.model_dump()
        
        assert isinstance(data, dict)
        assert data["type"] == "start"
        assert data["role"] == "assistant"


class TestLiteralTypes:
    """Tests for Literal type enforcement."""

    def test_transcript_type_literal(self):
        """TranscriptPayload type is always 'transcript'."""
        from app.core.schemas import TranscriptPayload
        
        # Even if we try to set a different type, it uses the Literal default
        payload = TranscriptPayload(text="Test", source="user")
        assert payload.type == "transcript"

    def test_chunk_type_literal(self):
        """ChunkPayload type is always 'chunk'."""
        from app.core.schemas import ChunkPayload
        
        payload = ChunkPayload(content="Test")
        assert payload.type == "chunk"

    def test_chat_type_literal(self):
        """ChatRequest type is always 'chat'."""
        from app.core.schemas import ChatRequest
        
        request = ChatRequest(message="Test")
        assert request.type == "chat"

