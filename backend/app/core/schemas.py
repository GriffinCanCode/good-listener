from pydantic import BaseModel
from typing import Literal

class WebSocketPayload(BaseModel):
    type: str

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

class AutoAnswerPayload(WebSocketPayload):
    type: Literal["auto_answer"] = "auto_answer"
    question: str
    content: str

class AutoAnswerChunkPayload(WebSocketPayload):
    type: Literal["auto_chunk"] = "auto_chunk"
    question: str
    content: str

class AutoAnswerStartPayload(WebSocketPayload):
    type: Literal["auto_start"] = "auto_start"
    question: str

class AutoAnswerDonePayload(WebSocketPayload):
    type: Literal["auto_done"] = "auto_done"
    question: str

class ChatRequest(WebSocketPayload):
    type: Literal["chat"] = "chat"
    message: str

class CaptureResponse(BaseModel):
    message: str
    extracted_text: str

class RecordingStatusResponse(BaseModel):
    status: str
