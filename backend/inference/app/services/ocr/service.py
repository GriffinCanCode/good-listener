import asyncio

import numpy as np
from PIL import Image

from app.core import get_logger

logger = get_logger(__name__)


class OCRService:
    def __init__(self) -> None:
        self._engine = None

    @property
    def engine(self):
        """Lazy-load RapidOCR on first use."""
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._engine = RapidOCR()
                logger.info("RapidOCR initialized.")
            except Exception:
                logger.exception("RapidOCR init failed")
        return self._engine

    def extract_text(self, image: Image.Image) -> str:
        if not self.engine or not image:
            return ""
        try:
            if not (result := self.engine(np.array(image))[0]):
                return ""
            return "\n".join(
                f"[{int(min(p[0] for p in r[0]))}, {int(min(p[1] for p in r[0]))}, {int(max(p[0] for p in r[0]))}, {int(max(p[1] for p in r[0]))}] {r[1]}"
                for r in result
                if r[1]
            )
        except Exception:
            logger.exception("OCR Error")
            return ""

    async def extract_text_async(self, image: Image.Image) -> str:
        return "" if not image else await asyncio.get_running_loop().run_in_executor(None, self.extract_text, image)
