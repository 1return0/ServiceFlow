from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from app.application.knowledge.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssembler,
)
from app.application.knowledge.support_knowledge_document_parsing_service import (
    SupportKnowledgeDocumentParsingService,
)
from app.application.knowledge.support_knowledge_ingestion_service import (
    SupportKnowledgeIngestionService,
)
from app.application.knowledge.knowledge_import_access_policy import (
    KnowledgeImportAccessPolicy,
)
from app.application.retrieval.support_knowledge_answering import (
    ExtractiveSupportKnowledgeAnswerService,
)
from app.application.retrieval.refreshable_support_knowledge_chunk_retriever import (
    RefreshableSupportKnowledgeChunkRetriever,
)
from app.application.knowledge.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
)
from app.application.knowledge.support_knowledge_parser_registry import (
    SupportKnowledgeParserRegistry,
)
from app.infrastructure.persistence.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
)
from app.infrastructure.parsers.html_support_knowledge_artifact_parser import (
    HtmlSupportKnowledgeArtifactParser,
)
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)
from app.main import app


class SupportKnowledgeImportApiTest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.import_token = "test-knowledge-import-secret"
        app.state.knowledge_import_access_policy = KnowledgeImportAccessPolicy(
            enabled=True,
            admin_token=self.import_token,
        )
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        app.state.support_knowledge_ingestion_service = SupportKnowledgeIngestionService(
            FileSystemSupportKnowledgeArtifactStore(root),
            SupportKnowledgeDocumentParsingService(
                SupportKnowledgeParserRegistry((
                    HtmlSupportKnowledgeArtifactParser(root),
                ))
            ),
            SupportKnowledgeArticleAssembler(),
            corpus,
            FragmentAwareSupportKnowledgeChunker(),
        )
        app.state.support_knowledge_answer_service = (
            ExtractiveSupportKnowledgeAnswerService(
                RefreshableSupportKnowledgeChunkRetriever(corpus)
            )
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()
        self.client.__exit__(None, None, None)

    def test_imports_a_reviewed_html_document(self) -> None:
        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": self.import_token},
            json={
                "source_reference": "https://it.example.edu/network-guide.html",
                "source_kind": "official_campus",
                "original_filename": "network-guide.html",
                "content_base64": base64.b64encode(
                    b"<title>Network Guide</title><p>Use CampusNet.</p>"
                ).decode("ascii"),
                "metadata": {
                    "article_id": "network-guide-v1",
                    "category": "campus_network",
                    "fallback_title": "Network guide",
                    "source_review_status": "reviewed",
                    "source_review_reference": "review-20260910",
                    "corpus_version": "campus-support-v2",
                },
            },
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual("html", response.json()["document_format"])
        self.assertEqual("network-guide-v1", response.json()["article_id"])
        self.assertGreater(response.json()["parsed_text_length"], 0)
        self.assertTrue(response.json()["corpus_changed"])
        self.assertEqual(1, response.json()["corpus_revision"])
        self.assertEqual(
            "https://it.example.edu/network-guide.html",
            response.json()["source_reference"],
        )
        self.assertEqual("reviewed", response.json()["source_review_status"])
        self.assertEqual("disabled", response.json()["dense_index_status"])
        self.assertIsNone(response.json()["dense_index_failure_code"])

        answer_response = self.client.post(
            "/api/v1/knowledge/answer",
            json={"question": "CampusNet 怎么使用？"},
        )
        self.assertEqual(200, answer_response.status_code)
        self.assertEqual("answered", answer_response.json()["status"])
        self.assertEqual("network-guide-v1", answer_response.json()["citations"][0]["article_id"])
        self.assertIsNotNone(answer_response.json()["citations"][0]["chunk_id"])
        self.assertEqual(
            "html:body",
            answer_response.json()["citations"][0]["fragment_location"],
        )

    def test_rejects_an_invalid_base64_payload_before_ingestion(self) -> None:
        response = self.client.post(
            "/api/v1/knowledge/imports",
            json={
                "source_reference": "https://it.example.edu/network-guide.html",
                "source_kind": "official_campus",
                "original_filename": "network-guide.html",
                "content_base64": "not-valid-base64!",
                "metadata": {
                    "article_id": "network-guide-v1",
                    "category": "campus_network",
                    "fallback_title": "Network guide",
                    "source_review_status": "reviewed",
                    "source_review_reference": "review-20260910",
                    "corpus_version": "campus-support-v2",
                },
            },
        )

        self.assertEqual(422, response.status_code)

    def test_refreshes_the_enabled_dense_index_after_import(self) -> None:
        class RecordingDenseIndexRuntime:
            refresh_calls = 0

            def refresh(self) -> None:
                self.refresh_calls += 1

        # The endpoint relies on the concrete runtime in production; this small
        # adapter keeps the HTTP contract test isolated from a real embedding API.
        runtime = RecordingDenseIndexRuntime()
        app.state.support_knowledge_dense_index_runtime = runtime
        try:
            response = self.client.post(
                "/api/v1/knowledge/imports",
                headers={"X-Knowledge-Import-Token": self.import_token},
                json=self._valid_import_payload(),
            )
        finally:
            del app.state.support_knowledge_dense_index_runtime

        self.assertEqual(201, response.status_code)
        self.assertEqual("ready", response.json()["dense_index_status"])
        self.assertEqual(1, runtime.refresh_calls)

    def test_hides_the_import_endpoint_when_the_deployment_keeps_it_disabled(self) -> None:
        app.state.knowledge_import_access_policy = KnowledgeImportAccessPolicy(
            enabled=False,
            admin_token=None,
        )

        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": self.import_token},
            json=self._valid_import_payload(),
        )

        self.assertEqual(404, response.status_code)

    def test_rejects_a_wrong_administrator_import_token_before_file_storage(self) -> None:
        response = self.client.post(
            "/api/v1/knowledge/imports",
            headers={"X-Knowledge-Import-Token": "wrong-token"},
            json=self._valid_import_payload(),
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual([], list(Path(self.temporary_directory.name).iterdir()))

    @staticmethod
    def _valid_import_payload() -> dict[str, object]:
        return {
            "source_reference": "https://it.example.edu/network-guide.html",
            "source_kind": "official_campus",
            "original_filename": "network-guide.html",
            "content_base64": base64.b64encode(
                b"<title>Network Guide</title><p>Use CampusNet.</p>"
            ).decode("ascii"),
            "metadata": {
                "article_id": "network-guide-v1",
                "category": "campus_network",
                "fallback_title": "Network guide",
                "source_review_status": "reviewed",
                "source_review_reference": "review-20260910",
                "corpus_version": "campus-support-v2",
            },
        }
