from __future__ import annotations

from unittest import TestCase

from app.application.knowledge.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssembler,
    SupportKnowledgeArticleAssemblyError,
)
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
)
from app.domain.support_knowledge import SupportKnowledgeArticleMetadata
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class SupportKnowledgeArticleAssemblerTest(TestCase):
    def setUp(self) -> None:
        self.artifact = SupportKnowledgeArtifact(
            artifact_id="artifact_network_guide",
            source_reference="https://it.example.edu/network-guide.pdf",
            source_kind="official_campus",
            document_format="pdf",
            storage_relative_path="artifacts/network-guide.pdf",
            byte_size=123,
            content_sha256="artifact-sha256",
        )
        self.metadata = SupportKnowledgeArticleMetadata(
            article_id="campus-network-guide-v1",
            category="campus_network",
            fallback_title="Campus network guide",
            source_reference=self.artifact.source_reference,
            source_kind="official_campus",
            source_review_status="reviewed",
            source_review_reference="review-record-20260909",
            corpus_version="campus-support-v2",
        )

    def test_combines_parsed_text_with_reviewed_metadata(self) -> None:
        article = SupportKnowledgeArticleAssembler().assemble(
            self.artifact,
            ParsedSupportKnowledgeDocument(
                artifact_id=self.artifact.artifact_id,
                document_format="pdf",
                title=None,
                text="Connect to CampusNet, then complete web authentication.",
            ),
            self.metadata,
        )

        self.assertEqual(article.title, "Campus network guide")
        self.assertEqual(article.category, "campus_network")
        self.assertEqual(article.source_reference, self.artifact.source_reference)
        self.assertTrue(article.source_content_sha256)

    def test_rejects_metadata_for_a_different_source(self) -> None:
        mismatched_metadata = SupportKnowledgeArticleMetadata(
            **{
                **self.metadata.__dict__,
                "source_reference": "https://it.example.edu/another-guide.pdf",
            }
        )

        with self.assertRaises(SupportKnowledgeArticleAssemblyError):
            SupportKnowledgeArticleAssembler().assemble(
                self.artifact,
                ParsedSupportKnowledgeDocument(
                    artifact_id=self.artifact.artifact_id,
                    document_format="pdf",
                    title="Network guide",
                    text="Use CampusNet.",
                ),
                mismatched_metadata,
            )
