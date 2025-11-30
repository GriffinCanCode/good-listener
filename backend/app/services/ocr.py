import asyncio
import logging
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self) -> None:
        try:
            self.engine = RapidOCR()
            logger.info("RapidOCR initialized.")
        except Exception as e:
            logger.error(f"RapidOCR init failed: {e}")
            self.engine = None

    def extract_text(self, image: Image.Image) -> str:
        if not self.engine: return ""
        try:
            result, _ = self.engine(np.array(image))
            return "\n".join(r[1] for r in result if r[1]).strip() if result else ""
        except Exception as e:
            logger.error(f"OCR Error: {e}")
            return ""

    async def extract_text_async(self, image: Image.Image) -> str:
        if not image: return ""
        return await asyncio.get_running_loop().run_in_executor(None, self.extract_text, image)
