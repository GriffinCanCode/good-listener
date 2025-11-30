import asyncio
from fastapi import APIRouter, HTTPException, Request
import logging

router = APIRouter(prefix="/api", tags=["api"])

logger = logging.getLogger(__name__)

@router.get("/capture")
async def capture_now(request: Request) -> dict[str, str]:
    """Triggers an immediate screen capture and OCR using the active monitor."""
    monitor = request.app.state.monitor
    
    if not monitor.latest_image:
        # Try to capture immediately if none cached
        monitor.capture_service.capture_screen()
        
    text = monitor.latest_text
    
    return {
        "message": "Screen processed", 
        "extracted_text": text[:500] + "..." if len(text) > 500 else text
    }

@router.post("/recording/start")
async def start_recording(request: Request):
    """Enable recording of transcripts and screen context to vector memory."""
    request.app.state.monitor.set_recording(True)
    return {"status": "recording_started"}

@router.post("/recording/stop")
async def stop_recording(request: Request):
    """Disable recording (live assistance continues, but no memory storage)."""
    request.app.state.monitor.set_recording(False)
    return {"status": "recording_stopped"}
