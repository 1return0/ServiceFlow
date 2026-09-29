from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


@dataclass(frozen=True)
class OcrPageText:
    """Text recognised from one rendered PDF page."""

    page_number: int
    text: str


class OcrTextExtractor(Protocol):
    """Infrastructure boundary for a real OCR engine such as PaddleOCR."""

    def extract_page_texts(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> tuple[OcrPageText, ...]:
        ...


@dataclass(frozen=True)
class RenderedPdfPage:
    """One PDF page rendered as PNG bytes for an OCR engine."""

    page_number: int
    width_pixels: int
    height_pixels: int
    png_bytes: bytes


class PdfPageRenderer(Protocol):
    """Renders validated PDF pages without exposing a vendor-specific library."""

    def render_pages(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> tuple[RenderedPdfPage, ...]:
        ...
