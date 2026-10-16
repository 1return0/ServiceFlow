from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

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
from app.application.knowledge.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
)
from app.domain.support_knowledge import SupportKnowledgeArticleMetadata
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)
from app.infrastructure.persistence.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
)
from app.infrastructure.parsers.html_support_knowledge_artifact_parser import (
    HtmlSupportKnowledgeArtifactParser,
)


class SupportKnowledgeIngestionServiceTest(TestCase):
    def test_stores_parses_and_assembles_a_reviewed_html_article(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            service = SupportKnowledgeIngestionService(
                FileSystemSupportKnowledgeArtifactStore(root),
                SupportKnowledgeDocumentParsingService(
                    SupportKnowledgeParserRegistry((
                        HtmlSupportKnowledgeArtifactParser(root),
                    ))
                ),
                SupportKnowledgeArticleAssembler(),
                InMemoryCurrentSupportKnowledgeCorpus(()),
                FragmentAwareSupportKnowledgeChunker(),
            )
            source_reference = "https://it.example.edu/network-guide.html"

            result = service.ingest(
                source_reference=source_reference,
                source_kind="official_campus",
                original_filename="network-guide.html",
                content=(
                    b"<html><title>Campus network</title>"
                    b"<body>Connect to CampusNet before class.</body></html>"
                ),
                metadata=SupportKnowledgeArticleMetadata(
                    article_id="campus-network-v1",
                    category="campus_network",
                    fallback_title="Network guide",
                    source_reference=source_reference,
                    source_kind="official_campus",
                    source_review_status="reviewed",
                    source_review_reference="manual-review-20260909",
                    corpus_version="campus-support-v2",
                ),
            )

            self.assertEqual(result.artifact.document_format, "html")
            self.assertIn("CampusNet", result.parsed_document.text)
            self.assertEqual(result.article.title, "Campus network")
            self.assertEqual(result.article.article_id, "campus-network-v1")
            self.assertTrue(result.corpus_changed)
            self.assertEqual(result.corpus_revision, 1)
            self.assertEqual(len(result.chunks), 1)
            self.assertEqual(result.chunks[0].fragment_location, "html:body")
