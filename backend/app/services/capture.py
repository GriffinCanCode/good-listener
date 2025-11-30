from typing import Optional

import mss
from PIL import Image

from app.core import get_logger

logger = get_logger(__name__)

class CaptureService:
    def __init__(self) -> None:
        self.sct = mss.mss()
        logger.info("CaptureService initialized")

    def capture_screen(self, monitor_index: int = 1) -> Optional[Image.Image]:
        """Captures the specified monitor and returns a PIL Image."""
        try:
            if monitor_index >= len(self.sct.monitors):
                logger.warning("Invalid monitor index", index=monitor_index, available=len(self.sct.monitors))
                return None
                
            monitor = self.sct.monitors[monitor_index]
            sct_img = self.sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            logger.error("Screen capture failed", error=str(e))
            return None

