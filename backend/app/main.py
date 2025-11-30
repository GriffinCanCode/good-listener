from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import json
import asyncio
from app.services.monitor import BackgroundMonitor
from app.services.llm import LLMService
from app.routers import api

monitor = BackgroundMonitor()
llm_service = LLMService(provider="ollama") 
active_connections: list[WebSocket] = []

async def broadcast_insight(message: str):
    """Sends a message to all connected WebSocket clients."""
    if not active_connections:
        return
    
    # Wrap in JSON for the frontend
    payload = json.dumps({
        "type": "insight",
        "content": message
    })
    
    # Create tasks for all sends to run concurrently
    tasks = [connection.send_text(payload) for connection in active_connections]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Cleanup broken connections
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # We can't easily remove from active_connections by index safely while iterating 
            # if we were iterating the list, but here we know which one failed.
            # Simpler: just let the websocket endpoint handle disconnects on read, 
            # or remove here if we want to be proactive.
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor.on_insight = broadcast_insight
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
                user_query = message_data.get("message", "")
                current_text = monitor.latest_text or "No text on screen."
                
                # Signal start of response
                await websocket.send_json({"type": "start", "role": "assistant"})
                
                # Stream chunks
                async for chunk in llm_service.analyze(current_text, user_query):
                    await websocket.send_json({"type": "chunk", "content": chunk})
                
                # Signal completion
                await websocket.send_json({"type": "done"})
                
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
