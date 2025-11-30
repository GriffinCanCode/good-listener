import asyncio
from fastapi import APIRouter, HTTPException
from app.services.capture import CaptureService
from app.services.ocr import OCRService
import logging

router = APIRouter(prefix="/api", tags=["api"])
capture_service = CaptureService()
ocr_service = OCRService()

logger = logging.getLogger(__name__)

@router.get("/capture")
async def capture_now() -> dict[str, str]:
    """Triggers an immediate screen capture and OCR."""
    if not (image := capture_service.capture_screen()):
        raise HTTPException(status_code=500, detail="Failed to capture screen")
    
    text = await asyncio.to_thread(ocr_service.extract_text, image)
    
    return {
        "message": "Screen processed", 
        "extracted_text": text[:500] + "..." if len(text) > 500 else text
    }
