import asyncio

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

from app.core import get_logger

logger = get_logger(__name__)

class OCRService:
    def __init__(self) -> None:
        try:
            self.engine = RapidOCR()
            logger.info("RapidOCR initialized.")
        except Exception as e:
            logger.error(f"RapidOCR init failed: {e}")
            self.engine = None

    def extract_text(self, image: Image.Image) -> str:
        if not self.engine or not image: return ""
        try:
            result, _ = self.engine(np.array(image))
            if not result: return ""
            
            lines = []
            for r in result:
                if not r[1]: continue
                xs, ys = [p[0] for p in r[0]], [p[1] for p in r[0]]
                lines.append(f"[{int(min(xs))}, {int(min(ys))}, {int(max(xs))}, {int(max(ys))}] {r[1]}")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"OCR Error: {e}")
            return ""

    async def extract_text_async(self, image: Image.Image) -> str:
        if not image: return ""
        return await asyncio.get_running_loop().run_in_executor(None, self.extract_text, image)
