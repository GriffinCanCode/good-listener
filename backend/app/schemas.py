from pydantic import BaseModel
from typing import Literal

class WebSocketPayload(BaseModel):
    type: str

class InsightPayload(WebSocketPayload):
    type: Literal["insight"] = "insight"
    content: str

class TranscriptPayload(WebSocketPayload):
    type: Literal["transcript"] = "transcript"
    text: str
    source: str

class ChunkPayload(WebSocketPayload):
    type: Literal["chunk"] = "chunk"
    content: str

class StartPayload(WebSocketPayload):
    type: Literal["start"] = "start"
    role: str = "assistant"

class DonePayload(WebSocketPayload):
    type: Literal["done"] = "done"

class ChatRequest(WebSocketPayload):
    type: Literal["chat"] = "chat"
    message: str

class CaptureResponse(BaseModel):
    message: str
    extracted_text: str

class RecordingStatusResponse(BaseModel):
    status: str
