import asyncio
import re
import time
from collections import deque
from typing import Callable, Optional, Tuple

from PIL import Image

from app.core import get_logger
from app.services.audio import AudioService
from app.services.capture import CaptureService
from app.services.memory import MemoryService
from app.services.ocr import OCRService

logger = get_logger(__name__)

# Question patterns for detection
QUESTION_STARTERS = re.compile(
    r'^(who|what|where|when|why|how|can|could|would|should|is|are|do|does|did|'
    r'have|has|will|won\'t|isn\'t|aren\'t|don\'t|doesn\'t|didn\'t|haven\'t|hasn\'t|'
    r'was|were|which|shall|may|might|tell me)\b',
    re.IGNORECASE
)

def is_question(text: str) -> bool:
    """Detect if text is a question directed at the user."""
    text = text.strip()
    if not text or len(text) < 10:
        return False
    # Explicit question mark
    if text.endswith('?'):
        return True
    # Question starter words
    return bool(QUESTION_STARTERS.match(text))

class BackgroundMonitor:
    def __init__(
        self,
        capture_service: CaptureService,
        ocr_service: OCRService,
        audio_service: AudioService,
        memory_service: MemoryService,
    ):
        self.capture_service = capture_service
        self.ocr_service = ocr_service
        self.audio_service = audio_service
        self.memory_service = memory_service
        
        self._running = False
        self._is_recording = True  # Controls writing to vector DB
        self._auto_answer_enabled = True  # Controls question detection
        self._tasks = set()
        self.transcript_queue = None
        # Store tuples of (timestamp, text, source)
        self.recent_transcripts: deque[Tuple[float, str, str]] = deque(maxlen=30)
        
        self.latest_text = ""
        self.latest_transcript = ""
        self.latest_image: Optional[Image.Image] = None
        self.on_transcript: Optional[Callable] = None  # Callback for live broadcasting
        self.on_question_detected: Optional[Callable] = None  # Callback for auto-answering

    async def start(self):
        self._running = True
        self.loop = asyncio.get_running_loop()
        self.transcript_queue = asyncio.Queue()
        
        self._tasks.add(asyncio.create_task(self._screen_loop()))
        self._tasks.add(asyncio.create_task(self._transcript_worker()))
        
        self.audio_service.start_listening(self._handle_transcript)
        logger.info("Background monitor started", recording=self._is_recording, auto_answer=self._auto_answer_enabled)

    async def stop(self):
        self._running = False
        self.audio_service.stop_listening()
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Background monitor stopped", transcripts_buffered=len(self.recent_transcripts))

    def _handle_transcript(self, text: str, source: str):
        if not self._running:
            return

        # Broadcast immediately for live UI
        if self.on_transcript:
            asyncio.run_coroutine_threadsafe(self.on_transcript(text, source), self.loop)

        if self.transcript_queue:
            self.loop.call_soon_threadsafe(self.transcript_queue.put_nowait, (text, source))

    async def _transcript_worker(self):
        while self._running:
            try:
                item = await self.transcript_queue.get()
                await self._process_transcript(item)
                self.transcript_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Transcript worker error", error=str(e))

    async def _process_transcript(self, item: Tuple[str, str]):
        text, source = item
        self.latest_transcript = text
        self.recent_transcripts.append((time.time(), text, source))
        
        # Store significant transcripts to memory
        if self._is_recording and len(text.split()) >= 4:
            self.memory_service.add_memory(f"{source.upper()}: {text}", "audio")
        
        # Detect questions from system audio (other person on call)
        if self._auto_answer_enabled and source == "system" and is_question(text):
            logger.info("Question detected", text=text[:80], source=source)
            if self.on_question_detected:
                asyncio.create_task(self.on_question_detected(text))
    
    def set_auto_answer(self, enabled: bool):
        self._auto_answer_enabled = enabled
        logger.info(f"Auto-answer set to: {enabled}")
    
    def get_recent_transcript(self, seconds: int = 120) -> str:
        """Get transcript from the last N seconds for context when user asks."""
        cutoff = time.time() - seconds
        return "\n".join(
            f"{src.upper()}: {t}" 
            for ts, t, src in self.recent_transcripts 
            if ts > cutoff
        )

    async def _screen_loop(self):
        consecutive_stable_checks = 0
        last_stored_text = ""
        last_visual_hash = None

        while self._running:
            try:
                if image := self.capture_service.capture_screen():
                    # Quick visual check using downsampling + hashing
                    # Resize to 32x32 to detect meaningful changes only
                    small_img = image.resize((32, 32), Image.Resampling.NEAREST).convert("L")
                    current_hash = hash(small_img.tobytes())

                    if current_hash == last_visual_hash:
                        await asyncio.sleep(0.5)
                        continue
                    
                    last_visual_hash = current_hash
                    self.latest_image = image
                    
                    text = await self.ocr_service.extract_text_async(image)
                    
                    if text != self.latest_text:
                         self.latest_text = text
                         consecutive_stable_checks = 0
                    else:
                        consecutive_stable_checks += 1

                    if (self._is_recording and 
                        consecutive_stable_checks >= 2 and 
                        text != last_stored_text and 
                        len(text) > 50):
                        
                        self.memory_service.add_memory(text, "screen")
                        last_stored_text = text
                        consecutive_stable_checks = 0
                        
            except Exception as e:
                logger.error(f"Screen loop error: {e}")
            
            await asyncio.sleep(1)

    def set_recording(self, active: bool):
        self._is_recording = active
        logger.info(f"Recording state set to: {active}")
