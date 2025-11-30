from contextlib import asynccontextmanager
import asyncio
import json
import time
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

from app.core import (
    get_logger, set_correlation_id,
    ChunkPayload, StartPayload, DonePayload, ChatRequest, TranscriptPayload,
    AutoAnswerStartPayload, AutoAnswerChunkPayload, AutoAnswerDonePayload,
)
from app.services import (
    BackgroundMonitor, LLMService, CaptureService, OCRService, AudioService, MemoryService,
)
from app.routers import router as api_router

logger = get_logger(__name__)

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
    
    logger.debug("Broadcasting transcript", source=source, clients=len(active_connections))
    payload = TranscriptPayload(text=text, source=source).model_dump_json()
    tasks = [connection.send_text(payload) for connection in active_connections]
    await asyncio.gather(*tasks, return_exceptions=True)

async def handle_question_detected(question: str):
    """Auto-generate answer when a question is detected in conversation."""
    global _last_auto_answer_time
    
    if not active_connections:
        return
    
    now = time.time()
    if now - _last_auto_answer_time < _auto_answer_cooldown:
        logger.debug("Auto-answer skipped (cooldown)", question=question[:50])
        return
    _last_auto_answer_time = now
    logger.info("Auto-answering question", question=question[:50])
    
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
    logger.info("Starting application")
    monitor.on_transcript = broadcast_transcript
    monitor.on_question_detected = handle_question_detected
    app.state.monitor = monitor
    await monitor.start()
    yield
    logger.info("Shutting down application")
    await monitor.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_id = str(uuid.uuid4())[:8]
    set_correlation_id(ws_id)
    
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("WebSocket connected", ws_id=ws_id, total_connections=len(active_connections))
    
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

                logger.info("Chat message received", query_len=len(user_query))
                
                screen_text = monitor.latest_text or ""
                transcript = monitor.get_recent_transcript(seconds=300)
                
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
        logger.info("WebSocket disconnected", ws_id=ws_id)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.error("WebSocket error", ws_id=ws_id, error=str(e))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
