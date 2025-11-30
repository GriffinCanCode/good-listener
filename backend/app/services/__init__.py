"""
Services: business logic and external integrations.
"""

from app.services.audio import AudioService, DeviceListener
from app.services.capture import CaptureService
from app.services.llm import LLMService
from app.services.memory import MemoryService
from app.services.monitor import BackgroundMonitor, is_question
from app.services.ocr import OCRService
from app.services.prompts import SYSTEM_PROMPT, ANALYSIS_TEMPLATE

__all__ = [
    "AudioService",
    "DeviceListener",
    "CaptureService",
    "LLMService",
    "MemoryService",
    "BackgroundMonitor",
    "is_question",
    "OCRService",
    "SYSTEM_PROMPT",
    "ANALYSIS_TEMPLATE",
]

