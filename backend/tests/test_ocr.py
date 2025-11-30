"""Tests for OCRService."""
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
import numpy as np


class TestOCRService:
    """Tests for OCR text extraction."""

    def test_init_success(self, mock_rapidocr):
        """OCRService initializes RapidOCR engine."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', return_value=mock_rapidocr):
            service = OCRService()
            assert service.engine is not None

    def test_init_failure(self):
        """OCRService handles init failure gracefully."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', side_effect=Exception("Init failed")):
            service = OCRService()
            assert service.engine is None

    def test_extract_text_success(self, mock_rapidocr):
        """extract_text returns formatted text with bounding boxes."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new('RGB', (200, 100), color='white')
            
            result = service.extract_text(image)
            
            assert "[0, 0, 100, 20] Hello World" in result
            assert "[0, 30, 150, 50] Test Text" in result

    def test_extract_text_no_engine(self):
        """extract_text returns empty string when engine not initialized."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', side_effect=Exception("Failed")):
            service = OCRService()
            image = Image.new('RGB', (100, 100))
            
            result = service.extract_text(image)
            
            assert result == ""

    def test_extract_text_no_image(self, mock_rapidocr):
        """extract_text returns empty string for None image."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', return_value=mock_rapidocr):
            service = OCRService()
            
            result = service.extract_text(None)
            
            assert result == ""

    def test_extract_text_no_results(self, mock_rapidocr):
        """extract_text handles empty OCR results."""
        from app.services.ocr import OCRService
        
        mock_rapidocr.return_value = (None, None)
        
        with patch('app.services.ocr.RapidOCR', return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new('RGB', (100, 100))
            
            result = service.extract_text(image)
            
            assert result == ""

    def test_extract_text_exception(self, mock_rapidocr):
        """extract_text handles OCR exceptions."""
        from app.services.ocr import OCRService
        
        mock_rapidocr.side_effect = Exception("OCR failed")
        
        with patch('app.services.ocr.RapidOCR') as MockOCR:
            MockOCR.return_value = mock_rapidocr
            service = OCRService()
            service.engine = mock_rapidocr
            image = Image.new('RGB', (100, 100))
            
            result = service.extract_text(image)
            
            assert result == ""

    @pytest.mark.asyncio
    async def test_extract_text_async(self, mock_rapidocr):
        """extract_text_async runs OCR in executor."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new('RGB', (200, 100))
            
            result = await service.extract_text_async(image)
            
            assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_extract_text_async_none_image(self, mock_rapidocr):
        """extract_text_async returns empty for None image."""
        from app.services.ocr import OCRService
        
        with patch('app.services.ocr.RapidOCR', return_value=mock_rapidocr):
            service = OCRService()
            
            result = await service.extract_text_async(None)
            
            assert result == ""

