from __future__ import annotations

from unittest import TestCase

from app.api.routes import _to_support_knowledge_import_http_exception
from app.application.ocr_page_reading_order import OcrPageSequenceError
from app.infrastructure.openai_compatible_vision_ocr_text_extractor import (
    OcrTextExtractorUnavailableError,
)
from app.infrastructure.pdf_page_rendering import PdfPagePixelLimitExceededError
from app.infrastructure.pdf_support_knowledge_artifact_parser import (
    PdfTextLayerMissingError,
)


class SupportKnowledgeImportFailureMappingTest(TestCase):
    def test_exposes_a_stable_code_for_a_pdf_without_text_layer(self) -> None:
        response = _to_support_knowledge_import_http_exception(
            PdfTextLayerMissingError("internal parser text")
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual("pdf-text-layer-missing", response.detail["code"])
        self.assertNotIn("internal parser text", response.detail["message"])

    def test_exposes_an_ocr_dependency_failure_as_503(self) -> None:
        response = _to_support_knowledge_import_http_exception(
            OcrTextExtractorUnavailableError("ocr-model-timeout")
        )

        self.assertEqual(503, response.status_code)
        self.assertEqual("ocr-model-timeout", response.detail["code"])

    def test_keeps_pixel_limit_and_sequence_failures_distinct(self) -> None:
        pixel_limit = _to_support_knowledge_import_http_exception(
            PdfPagePixelLimitExceededError("raw internal value")
        )
        sequence = _to_support_knowledge_import_http_exception(
            OcrPageSequenceError("raw internal value")
        )

        self.assertEqual("pdf-page-pixel-limit-exceeded", pixel_limit.detail["code"])
        self.assertEqual("ocr-page-sequence-invalid", sequence.detail["code"])
