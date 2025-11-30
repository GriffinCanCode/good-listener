import pytesseract
from PIL import Image
import sys

class OCRService:
    def __init__(self) -> None:
        # Ensure tesseract is in path or configured here if needed
        pass

    def extract_text(self, image: Image.Image) -> str:
        """Extracts text from a PIL Image using Tesseract OCR."""
        try:
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

