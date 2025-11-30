from fastapi import APIRouter, Request

from app.core import get_logger, CaptureResponse, RecordingStatusResponse

router = APIRouter(prefix="/api", tags=["api"])
logger = get_logger(__name__)

@router.get("/capture", response_model=CaptureResponse)
async def capture_now(request: Request) -> CaptureResponse:
    """Triggers an immediate screen capture and OCR using the active monitor."""
    monitor = request.app.state.monitor
    
    if not monitor.latest_image:
        # Try to capture immediately if none cached
        monitor.capture_service.capture_screen()
        
    text = monitor.latest_text
    
    return CaptureResponse(
        message="Screen processed", 
        extracted_text=text[:500] + "..." if len(text) > 500 else text
    )

@router.post("/recording/start", response_model=RecordingStatusResponse)
async def start_recording(request: Request) -> RecordingStatusResponse:
    """Enable recording of transcripts and screen context to vector memory."""
    request.app.state.monitor.set_recording(True)
    return RecordingStatusResponse(status="recording_started")

@router.post("/recording/stop", response_model=RecordingStatusResponse)
async def stop_recording(request: Request) -> RecordingStatusResponse:
    """Disable recording (live assistance continues, but no memory storage)."""
    request.app.state.monitor.set_recording(False)
    return RecordingStatusResponse(status="recording_stopped")
