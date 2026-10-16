from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from app.main import app
from app.application.knowledge.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
)
from app.application.knowledge.knowledge_import_access_policy import KnowledgeImportAccessPolicy
from app.application.knowledge.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssembler,
)
from app.application.knowledge.support_knowledge_document_parsing_service import (
    SupportKnowledgeDocumentParsingService,
)
from app.application.knowledge.support_knowledge_ingestion_service import (
    SupportKnowledgeIngestionService,
)
from app.application.knowledge.support_knowledge_parser_registry import (
    SupportKnowledgeParserRegistry,
)
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
    ParsedSupportKnowledgeFragment,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.persistence.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
)
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)
from app.infrastructure.models.openai_compatible_vision_ocr_text_extractor import (
    OcrTextExtractorUnavailableError,
)
from app.infrastructure.parsers.pdf_ocr_fallback_support_knowledge_artifact_parser import (
    OcrTextExtractionEmptyError,
)
from app.infrastructure.parsers.pdf_page_rendering import PdfPagePixelLimitExceededError


class SupportKnowledgeOcrImportEndToEndTest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        app.state.knowledge_import_access_policy = KnowledgeImportAccessPolicy(
            enabled=True,
            admin_token="ocr-import-test-token",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()
        self.client.__exit__(None, None, None)

    def test_successful_ocr_pdf_import_becomes_a_chunk_with_ocr_location(self) -> None:
        self._install_service(_SuccessfulOcrPdfParser())

        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": "ocr-import-test-token"},
            json=self._payload(),
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual("pdf", response.json()["document_format"])
        self.assertTrue(response.json()["corpus_changed"])
        self.assertEqual(1, response.json()["corpus_revision"])
        _, chunks = self.corpus.chunk_snapshot()
        self.assertEqual(("page:1:ocr",), tuple(chunk.fragment_location for chunk in chunks))

    def test_ocr_model_timeout_returns_503_without_a_corpus_write(self) -> None:
        self._install_service(_FailingOcrPdfParser(OcrTextExtractorUnavailableError("ocr-model-timeout")))

        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": "ocr-import-test-token"},
            json=self._payload(),
        )

        self.assertEqual(503, response.status_code)
        self.assertEqual("ocr-model-timeout", response.json()["detail"]["code"])
        self.assertEqual(0, self.corpus.revision)
        self.assertEqual(1, len(tuple(self.root.iterdir())))

    def test_empty_ocr_text_returns_422_without_a_corpus_write(self) -> None:
        self._install_service(_FailingOcrPdfParser(OcrTextExtractionEmptyError("no text")))

        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": "ocr-import-test-token"},
            json=self._payload(),
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual("ocr-no-text-extracted", response.json()["detail"]["code"])
        self.assertEqual(0, self.corpus.revision)

    def test_pixel_limit_returns_422_without_a_corpus_write(self) -> None:
        self._install_service(
            _FailingOcrPdfParser(PdfPagePixelLimitExceededError("too large"))
        )

        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": "ocr-import-test-token"},
            json=self._payload(),
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual(
            "pdf-page-pixel-limit-exceeded", response.json()["detail"]["code"]
        )
        self.assertEqual(0, self.corpus.revision)

    def _install_service(self, parser: object) -> None:
        app.state.support_knowledge_ingestion_service = SupportKnowledgeIngestionService(
            FileSystemSupportKnowledgeArtifactStore(self.root),
            SupportKnowledgeDocumentParsingService(
                SupportKnowledgeParserRegistry((parser,))  # type: ignore[arg-type]
            ),
            SupportKnowledgeArticleAssembler(),
            self.corpus,
            FragmentAwareSupportKnowledgeChunker(),
        )

    @staticmethod
    def _payload() -> dict[str, object]:
        return {
            "source_reference": "synthetic://campus-support/ocr-import-v1",
            "source_kind": "demonstration",
            "original_filename": "scan.pdf",
            "content_base64": base64.b64encode(b"synthetic scan bytes").decode("ascii"),
            "metadata": {
                "article_id": "ocr-campus-support-v1",
                "category": "service_process",
                "fallback_title": "Campus support scan",
                "source_review_status": "demonstration",
                "source_review_reference": "ocr-e2e-test-v1",
                "corpus_version": "ocr-import-v1",
            },
        }


class _SuccessfulOcrPdfParser:
    document_format = "pdf"

    def parse(self, artifact: SupportKnowledgeArtifact) -> ParsedSupportKnowledgeDocument:
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="pdf",
            title=None,
            text="Campus IT Support\nLocation: Library 1F",
            fragments=(
                ParsedSupportKnowledgeFragment(
                    ordinal=1,
                    location="page:1:ocr",
                    text="Campus IT Support\nLocation: Library 1F",
                ),
            ),
        )


class _FailingOcrPdfParser:
    document_format = "pdf"

    def __init__(self, error: Exception) -> None:
        self._error = error

    def parse(self, artifact: SupportKnowledgeArtifact) -> ParsedSupportKnowledgeDocument:
        raise self._error
