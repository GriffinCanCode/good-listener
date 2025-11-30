import mss
import numpy as np
from PIL import Image
from typing import Optional

class CaptureService:
    def __init__(self) -> None:
        self.sct = mss.mss()

    def capture_screen(self, monitor_index: int = 1) -> Optional[Image.Image]:
        """Captures the specified monitor and returns a PIL Image."""
        try:
            # mss monitors are 1-indexed for actual screens (0 is 'all monitors')
            if monitor_index >= len(self.sct.monitors):
                return None
                
            monitor = self.sct.monitors[monitor_index]
            sct_img = self.sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None

