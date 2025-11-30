import asyncio

import numpy as np
from PIL import Image

import app.pb.cognition_pb2 as pb
from app.core import OCRError, get_logger

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
            except Exception as e:
                logger.exception("RapidOCR init failed")
                raise OCRError("Failed to initialize OCR engine", code=pb.OCR_INIT_FAILED, cause=e) from e
        return self._engine

    def extract_text(self, image: Image.Image) -> str:
        if not image:
            return ""
        try:
            if not (result := self.engine(np.array(image))[0]):
                return ""
            return "\n".join(
                f"[{int(min(p[0] for p in r[0]))}, {int(min(p[1] for p in r[0]))}, {int(max(p[0] for p in r[0]))}, {int(max(p[1] for p in r[0]))}] {r[1]}"
                for r in result
                if r[1]
            )
        except OCRError:
            raise
        except Exception as e:
            logger.exception("OCR Error")
            raise OCRError("Text extraction failed", code=pb.OCR_EXTRACT_FAILED, cause=e) from e

    async def extract_text_async(self, image: Image.Image) -> str:
        return "" if not image else await asyncio.get_running_loop().run_in_executor(None, self.extract_text, image)
