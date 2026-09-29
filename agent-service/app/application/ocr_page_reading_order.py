from __future__ import annotations

from app.domain.ocr_text_extraction import OcrPageText


class OcrPageSequenceError(ValueError):
    """OCR page results cannot be mapped back to one stable PDF page sequence."""


class OcrPageReadingOrderNormalizer:
    """Validate page identities, then restore the original PDF page order."""

    def normalize(
        self,
        pages: tuple[OcrPageText, ...],
    ) -> tuple[OcrPageText, ...]:
        page_numbers = tuple(page.page_number for page in pages)
        if any(page_number < 1 for page_number in page_numbers):
            raise OcrPageSequenceError("OCR page numbers must be at least 1")
        if len(set(page_numbers)) != len(page_numbers):
            raise OcrPageSequenceError("OCR output contains duplicate PDF page numbers")
        return tuple(sorted(pages, key=lambda page: page.page_number))
