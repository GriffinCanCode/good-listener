import asyncio
import logging
from typing import Optional
from PIL import Image
from app.services.capture import CaptureService
from app.services.ocr import OCRService
from app.services.analysis import AnalysisService
from app.services.audio import AudioService
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

class BackgroundMonitor:
    def __init__(self):
        self.capture_service = CaptureService()
        self.ocr_service = OCRService()
        self.analysis_service = AnalysisService()
        self.audio_service = AudioService() # Using 'tiny' model for speed
        self.llm_service = LLMService(provider="gemini", model_name="gemini-2.0-flash") # Explicitly set Gemini 2.0 Flash
        
        self._running = False
        self._task = None
        self.latest_insight = ""
        self.latest_text = ""
        self.latest_transcript = ""
        self.latest_image: Optional[Image.Image] = None
        
        # Callback for WebSocket push (set by main.py)
        self.on_insight = None

    async def start(self):
        self._running = True
        self.loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._screen_loop())
        
        # Start Audio Listening
        self.audio_service.start_listening(self._handle_transcript)
        logger.info("Background monitor started.")

    async def stop(self):
        self._running = False
        self.audio_service.stop_listening()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background monitor stopped.")

    def _handle_transcript(self, text: str):
        """Called by AudioService thread when text is transcribed."""
        if self._running and hasattr(self, 'loop'):
             asyncio.run_coroutine_threadsafe(self._process_transcript_async(text), self.loop)

    async def _process_transcript_async(self, text: str):
        self.latest_transcript = text
        
        screen_context = self.latest_text[:500] if self.latest_text else "No readable text on screen."
        
        prompt = f"""
        The user is in a conversation.
        Live Transcript: "{text}"
        Screen Text Context: "{screen_context}"
        
        If the transcript contains a question or requires a factual lookup about the screen, provide a direct answer.
        If the screen has no text but the user asks about it, describe the visual content.
        If it's just chatter/greeting, reply with "NO_RESPONSE".
        """
        
        # Call async LLM service with image
        response_parts = []
        async for chunk in self.llm_service.analyze(self.latest_text, prompt, self.latest_image):
            response_parts.append(chunk)
        response = "".join(response_parts)
        
        if response and "NO_RESPONSE" not in response:
            self.latest_insight = f"🎤 {text}\n💡 {response}"
            if self.on_insight:
                await self.on_insight(self.latest_insight)

    async def _screen_loop(self):
        while self._running:
            try:
                await self._process_screen()
            except Exception as e:
                logger.error(f"Error in screen loop: {e}")
            
            await asyncio.sleep(5)

    async def _process_screen(self):
        if not (image := self.capture_service.capture_screen()):
            return
        
        self.latest_image = image

        # Use async OCR
        text = await self.ocr_service.extract_text_async(image)
        
        # Update text even if empty (so we know it's empty)
        self.latest_text = text
