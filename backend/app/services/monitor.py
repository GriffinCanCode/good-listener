import asyncio
import logging
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
        self.llm_service = LLMService()
        
        self._running = False
        self._task = None
        self.latest_insight = ""
        self.latest_text = ""
        self.latest_transcript = ""
        
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
        # Schedule processing on the main event loop to avoid blocking the audio thread
        if self._running and hasattr(self, 'loop'):
             asyncio.run_coroutine_threadsafe(self._process_transcript_async(text), self.loop)

    async def _process_transcript_async(self, text: str):
        self.latest_transcript = text
        
        prompt = f"""
        The user is in a conversation.
        Live Transcript: "{text}"
        Screen Context: "{self.latest_text[:500]}..."
        
        If the transcript contains a question or requires a factual lookup, provide a direct, short answer. 
        If it's just chatter/greeting, reply with "NO_RESPONSE".
        """
        
        # Call async LLM service
        response_parts = []
        async for chunk in self.llm_service.analyze(self.latest_text, prompt):
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

        if not (text := await asyncio.to_thread(self.ocr_service.extract_text, image)):
            return

        self.latest_text = text
        # OCR analysis is less urgent than audio, so we don't push every update
        # unless specific keywords are found (handled in AnalysisService if linked)
