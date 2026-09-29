from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.domain.support_knowledge import SupportKnowledgeArticle
from app.infrastructure.json_file_current_support_knowledge_corpus import (
    JsonFileCurrentSupportKnowledgeCorpus,
)
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


def _article() -> SupportKnowledgeArticle:
    return SupportKnowledgeArticle(
        article_id="network-guide-v1", category="campus_network",
        title="Campus network", content="Connect to CampusNet.",
        source_reference="https://it.example.edu/network-guide.html",
        source_kind="official_campus",
        source_content_sha256="9ac2c1cd03ff498659e4766b65b068fcf9bbd137414f4a33836c94049ed93297",
        source_review_status="reviewed", source_review_reference="review-20260911",
        corpus_version="campus-support-v2",
    )


class JsonFileCurrentSupportKnowledgeCorpusTest(TestCase):
    def test_restores_a_successfully_imported_article_after_restart(self) -> None:
        with TemporaryDirectory() as directory:
            state_path = Path(directory) / "current-corpus.json"
            first = JsonFileCurrentSupportKnowledgeCorpus((), state_path)
            self.assertTrue(first.upsert(_article()))

            restarted = JsonFileCurrentSupportKnowledgeCorpus((), state_path)

            self.assertEqual(restarted.revision, 0)
            self.assertEqual(
                restarted.list_articles()[0].article_id,
                "network-guide-v1",
            )

    def test_restores_persisted_chunks_with_their_source_location(self) -> None:
        with TemporaryDirectory() as directory:
            state_path = Path(directory) / "current-corpus.json"
            article = _article()
            chunk = SupportKnowledgeChunk(
                "chunk-1", article.article_id, "CampusNet", 1,
                "paragraph:1:item:1", 0, 9, "fragment-aware-v2",
            )
            JsonFileCurrentSupportKnowledgeCorpus((), state_path).upsert_with_chunks(
                article, (chunk,)
            )

            restarted = JsonFileCurrentSupportKnowledgeCorpus((), state_path)
            self.assertEqual(restarted.chunk_snapshot()[1], (chunk,))
