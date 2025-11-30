"""Tests for OCRService."""

from unittest.mock import patch

import pytest
from PIL import Image


class TestOCRService:
    """Tests for OCR text extraction."""

    def test_init_success(self, mock_rapidocr):
        """OCRService initializes RapidOCR engine."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            assert service.engine is not None

    def test_init_failure(self):
        """OCRService handles init failure gracefully."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", side_effect=Exception("Init failed")):
            service = OCRService()
            assert service.engine is None

    def test_extract_text_success(self, mock_rapidocr):
        """extract_text returns formatted text with bounding boxes."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (200, 100), color="white")

            result = service.extract_text(image)

            assert "[0, 0, 100, 20] Hello World" in result
            assert "[0, 30, 150, 50] Test Text" in result

    def test_extract_text_no_engine(self):
        """extract_text returns empty string when engine not initialized."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", side_effect=Exception("Failed")):
            service = OCRService()
            image = Image.new("RGB", (100, 100))

            result = service.extract_text(image)

            assert result == ""

    def test_extract_text_no_image(self, mock_rapidocr):
        """extract_text returns empty string for None image."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()

            result = service.extract_text(None)

            assert result == ""

    def test_extract_text_no_results(self, mock_rapidocr):
        """extract_text handles empty OCR results."""
        from app.services.ocr import OCRService

        mock_rapidocr.return_value = (None, None)

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (100, 100))

            result = service.extract_text(image)

            assert result == ""

    def test_extract_text_exception(self, mock_rapidocr):
        """extract_text handles OCR exceptions."""
        from app.services.ocr import OCRService

        mock_rapidocr.side_effect = Exception("OCR failed")

        with patch("app.services.ocr.service.RapidOCR") as MockOCR:
            MockOCR.return_value = mock_rapidocr
            service = OCRService()
            service.engine = mock_rapidocr
            image = Image.new("RGB", (100, 100))

            result = service.extract_text(image)

            assert result == ""

    @pytest.mark.asyncio
    async def test_extract_text_async(self, mock_rapidocr):
        """extract_text_async runs OCR in executor."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (200, 100))

            result = await service.extract_text_async(image)

            assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_extract_text_async_none_image(self, mock_rapidocr):
        """extract_text_async returns empty for None image."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()

            result = await service.extract_text_async(None)

            assert result == ""


class TestOCRBoundingBoxes:
    """Tests for bounding box formatting."""

    def test_bounding_box_format(self, mock_rapidocr):
        """extract_text formats bounding boxes correctly."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (200, 100))

            result = service.extract_text(image)

            # Should contain [x1, y1, x2, y2] format
            assert "[0, 0, 100, 20]" in result

    def test_multiple_text_regions(self, mock_rapidocr):
        """extract_text handles multiple text regions."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (200, 100))

            result = service.extract_text(image)
            lines = result.split("\n")

            assert len(lines) == 2

    def test_empty_text_region_skipped(self, mock_rapidocr):
        """extract_text skips regions with empty text."""
        from app.services.ocr import OCRService

        mock_rapidocr.return_value = (
            [
                [[[0, 0], [100, 0], [100, 20], [0, 20]], "Valid", 0.95],
                [[[0, 30], [150, 30], [150, 50], [0, 50]], "", 0.92],  # Empty text
                [[[0, 30], [150, 30], [150, 50], [0, 50]], None, 0.92],  # None text
            ],
            None,
        )

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (200, 100))

            result = service.extract_text(image)

            assert "Valid" in result
            assert result.count("\n") == 0  # Only one valid line


class TestOCRImageFormats:
    """Tests for different image formats."""

    def test_extract_text_rgba_image(self, mock_rapidocr):
        """extract_text handles RGBA images."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))

            result = service.extract_text(image)

            assert "Hello World" in result

    def test_extract_text_grayscale_image(self, mock_rapidocr):
        """extract_text handles grayscale images."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("L", (100, 100), color=128)

            result = service.extract_text(image)

            assert "Hello World" in result

    def test_extract_text_large_image(self, mock_rapidocr):
        """extract_text handles large images."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (4000, 3000))

            result = service.extract_text(image)

            assert isinstance(result, str)

    def test_extract_text_small_image(self, mock_rapidocr):
        """extract_text handles very small images."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (10, 10))

            result = service.extract_text(image)

            assert isinstance(result, str)


class TestOCRAsync:
    """Tests for async OCR operations."""

    @pytest.mark.asyncio
    async def test_extract_text_async_concurrent(self, mock_rapidocr):
        """extract_text_async can run concurrently."""
        import asyncio

        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (100, 100))

            # Run multiple async extractions
            tasks = [service.extract_text_async(image) for _ in range(5)]
            results = await asyncio.gather(*tasks)

            assert all("Hello World" in r for r in results)

    @pytest.mark.asyncio
    async def test_extract_text_async_preserves_result(self, mock_rapidocr):
        """extract_text_async preserves result from sync method."""
        from app.services.ocr import OCRService

        with patch("app.services.ocr.service.RapidOCR", return_value=mock_rapidocr):
            service = OCRService()
            image = Image.new("RGB", (200, 100))

            sync_result = service.extract_text(image)
            async_result = await service.extract_text_async(image)

            assert sync_result == async_result
