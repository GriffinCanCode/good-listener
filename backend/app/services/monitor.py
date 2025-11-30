import asyncio
import logging
from typing import Optional
from PIL import Image
from app.services.capture import CaptureService
from app.services.ocr import OCRService
from app.services.analysis import AnalysisService
from app.services.audio import AudioService
from app.services.llm import LLMService
from app.services.memory import MemoryService
from app.services.prompts import get_monitor_prompt

logger = logging.getLogger(__name__)

class BackgroundMonitor:
    def __init__(
        self,
        capture_service: CaptureService,
        ocr_service: OCRService,
        analysis_service: AnalysisService,
        audio_service: AudioService,
        memory_service: MemoryService,
        llm_service: LLMService,
    ):
        self.capture_service = capture_service
        self.ocr_service = ocr_service
        self.analysis_service = analysis_service
        self.audio_service = audio_service
        self.memory_service = memory_service
        self.llm_service = llm_service
        
        self._running = False
        self._is_recording = True # Controls writing to vector DB
        self._tasks = set()
        self.transcript_queue = None
        
        self.latest_insight = ""
        self.latest_text = ""
        self.latest_transcript = ""
        self.latest_image: Optional[Image.Image] = None
        self.on_insight = None

    async def start(self):
        self._running = True
        self.loop = asyncio.get_running_loop()
        self.transcript_queue = asyncio.Queue()
        
        self._tasks.add(asyncio.create_task(self._screen_loop()))
        self._tasks.add(asyncio.create_task(self._transcript_worker()))
        
        self.audio_service.start_listening(self._handle_transcript)
        logger.info("Background monitor started.")

    async def stop(self):
        self._running = False
        self.audio_service.stop_listening()
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Background monitor stopped.")

    def _handle_transcript(self, text: str):
        if self._running and self.transcript_queue:
            self.loop.call_soon_threadsafe(self.transcript_queue.put_nowait, text)

    async def _transcript_worker(self):
        while self._running:
            try:
                text = await self.transcript_queue.get()
                await self._process_transcript(text)
                self.transcript_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Transcript worker error: {e}")

    async def _process_transcript(self, text: str):
        self.latest_transcript = text
        
        # Only store significant transcripts to avoid bloat
        # 1. Check length (ignore "Um", "Okay", etc.)
        # 2. Check recording state
        if self._is_recording and len(text.split()) >= 4:
            self.memory_service.add_memory(text, "audio")
        
        screen_ctx = self.latest_text[:500] if self.latest_text else "No readable text."
        prompt = get_monitor_prompt(text, screen_ctx)
        
        response = ""
        async for chunk in self.llm_service.analyze(self.latest_text, prompt, self.latest_image):
            response += chunk
        
        if response and "NO_RESPONSE" not in response:
            self.latest_insight = f"🎤 {text}\n💡 {response}"
            if self.on_insight:
                await self.on_insight(self.latest_insight)

    async def _screen_loop(self):
        consecutive_stable_checks = 0
        last_stored_text = ""

        while self._running:
            try:
                if image := self.capture_service.capture_screen():
                    self.latest_image = image
                    text = await self.ocr_service.extract_text_async(image)
                    
                    # Debounce/Stabilize: Only update if text changes
                    if text != self.latest_text:
                         self.latest_text = text
                         consecutive_stable_checks = 0
                    else:
                        consecutive_stable_checks += 1

                    # Store only if stable for a few cycles and different from what we last stored
                    # and contains enough content
                    if (self._is_recording and 
                        consecutive_stable_checks == 2 and 
                        text != last_stored_text and 
                        len(text) > 50):
                        
                        self.memory_service.add_memory(text, "screen")
                        last_stored_text = text
                        
            except Exception as e:
                logger.error(f"Screen loop error: {e}")
            await asyncio.sleep(5)

    def set_recording(self, active: bool):
        self._is_recording = active
        logger.info(f"Recording state set to: {active}")
