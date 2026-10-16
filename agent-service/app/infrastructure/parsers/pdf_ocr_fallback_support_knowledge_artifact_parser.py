from __future__ import annotations

from app.domain.ocr_text_extraction import OcrTextExtractor
from app.application.knowledge.ocr_page_reading_order import OcrPageReadingOrderNormalizer
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
    ParsedSupportKnowledgeFragment,
    SupportKnowledgeArtifactParseError,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.parsers.pdf_support_knowledge_artifact_parser import (
    PdfSupportKnowledgeArtifactParser,
    PdfTextLayerMissingError,
)


class OcrTextExtractionEmptyError(SupportKnowledgeArtifactParseError):
    """OCR completed but produced no usable visible text."""


class PdfOcrFallbackSupportKnowledgeArtifactParser:
    """Use normal PDF extraction first and OCR only for missing text layers."""

    def __init__(
        self,
        text_layer_parser: PdfSupportKnowledgeArtifactParser,
        ocr_text_extractor: OcrTextExtractor,
        reading_order_normalizer: OcrPageReadingOrderNormalizer | None = None,
    ) -> None:
        self._text_layer_parser = text_layer_parser
        self._ocr_text_extractor = ocr_text_extractor
        self._reading_order_normalizer = (
            reading_order_normalizer or OcrPageReadingOrderNormalizer()
        )

    @property
    def document_format(self) -> str:
        return "pdf"

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        try:
            return self._text_layer_parser.parse(artifact)
        except PdfTextLayerMissingError:
            return self._parse_with_ocr(artifact)

    def _parse_with_ocr(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        page_texts = self._reading_order_normalizer.normalize(
            self._ocr_text_extractor.extract_page_texts(artifact)
        )
        fragments = tuple(
            ParsedSupportKnowledgeFragment(
                ordinal=ordinal,
                location=f"page:{page.page_number}:ocr",
                text=page.text.strip(),
            )
            for ordinal, page in enumerate(page_texts, start=1)
            if page.text.strip()
        )
        text = "\n".join(fragment.text for fragment in fragments)
        if not text:
            raise OcrTextExtractionEmptyError(
                "OCR produced no extractable text for PDF artifact"
            )
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="pdf",
            title=None,
            text=text,
            fragments=fragments,
        )

    def close(self) -> None:
        close = getattr(self._ocr_text_extractor, "close", None)
        if callable(close):
            close()
