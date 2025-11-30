from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import json
import asyncio
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.schemas import (
    ChunkPayload, StartPayload, DonePayload, ChatRequest, TranscriptPayload,
    AutoAnswerStartPayload, AutoAnswerChunkPayload, AutoAnswerDonePayload
)
from app.services.monitor import BackgroundMonitor
from app.services.llm import LLMService
from app.services.capture import CaptureService
from app.services.ocr import OCRService
from app.services.audio import AudioService
from app.services.memory import MemoryService
from app.routers import api

# Instantiate services
capture_service = CaptureService()
ocr_service = OCRService()
# Enable system audio capture for phone calls
audio_service = AudioService(capture_system_audio=True)
memory_service = MemoryService()
llm_service = LLMService(provider="gemini", model_name="gemini-2.0-flash", memory_service=memory_service)

monitor = BackgroundMonitor(
    capture_service=capture_service,
    ocr_service=ocr_service,
    audio_service=audio_service,
    memory_service=memory_service,
)

active_connections: list[WebSocket] = []
_last_auto_answer_time: float = 0
_auto_answer_cooldown: float = 10.0  # Seconds between auto-answers

async def broadcast_transcript(text: str, source: str):
    """Sends a live transcript to all connected WebSocket clients."""
    if not active_connections:
        return
        
    payload = TranscriptPayload(text=text, source=source).model_dump_json()
    tasks = [connection.send_text(payload) for connection in active_connections]
    await asyncio.gather(*tasks, return_exceptions=True)

async def handle_question_detected(question: str):
    """Auto-generate answer when a question is detected in conversation."""
    global _last_auto_answer_time
    
    if not active_connections:
        return
    
    # Cooldown to prevent spam
    now = time.time()
    if now - _last_auto_answer_time < _auto_answer_cooldown:
        return
    _last_auto_answer_time = now
    
    # Build context from recent transcript and screen
    transcript = monitor.get_recent_transcript(seconds=120)
    screen_text = monitor.latest_text or ""
    
    context_parts = []
    if transcript:
        context_parts.append(f"RECENT CONVERSATION:\n{transcript}")
    if screen_text:
        context_parts.append(f"SCREEN TEXT:\n{screen_text[:2000]}")
    
    context = "\n\n".join(context_parts) or "No context available."
    
    # Notify all clients that auto-answer is starting
    start_payload = AutoAnswerStartPayload(question=question).model_dump_json()
    await asyncio.gather(*[c.send_text(start_payload) for c in active_connections], return_exceptions=True)
    
    # Stream the LLM response
    async for chunk in llm_service.analyze(context, question, monitor.latest_image):
        if active_connections:
            chunk_payload = AutoAnswerChunkPayload(question=question, content=chunk).model_dump_json()
            await asyncio.gather(*[c.send_text(chunk_payload) for c in active_connections], return_exceptions=True)
    
    # Notify completion
    done_payload = AutoAnswerDonePayload(question=question).model_dump_json()
    await asyncio.gather(*[c.send_text(done_payload) for c in active_connections], return_exceptions=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor.on_transcript = broadcast_transcript
    monitor.on_question_detected = handle_question_detected
    app.state.monitor = monitor
    await monitor.start()
    yield
    await monitor.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat":
                try:
                    chat_req = ChatRequest(**message_data)
                    user_query = chat_req.message
                except Exception:
                    continue

                # Build context: screen text + recent transcript
                screen_text = monitor.latest_text or ""
                transcript = monitor.get_recent_transcript(seconds=300)  # Last 5 min
                
                context_parts = []
                if transcript:
                    context_parts.append(f"RECENT CONVERSATION:\n{transcript}")
                if screen_text:
                    context_parts.append(f"SCREEN TEXT:\n{screen_text[:2000]}")
                
                context = "\n\n".join(context_parts) or "No context available."
                
                await websocket.send_json(StartPayload().model_dump())
                async for chunk in llm_service.analyze(context, user_query, monitor.latest_image):
                    await websocket.send_json(ChunkPayload(content=chunk).model_dump())
                await websocket.send_json(DonePayload().model_dump())
                
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
