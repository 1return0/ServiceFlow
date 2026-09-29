from __future__ import annotations

from unittest import TestCase

from app.domain.support_knowledge import SupportKnowledgeArticle
from app.infrastructure.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
    SupportKnowledgeCorpusConflictError,
)
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


def _article(*, article_id: str, source_content_sha256: str) -> SupportKnowledgeArticle:
    return SupportKnowledgeArticle(
        article_id=article_id,
        category="campus_network",
        title="Campus network",
        content="Connect to CampusNet.",
        source_reference="https://it.example.edu/network-guide.html",
        source_kind="official_campus",
        source_content_sha256=source_content_sha256,
        source_review_status="reviewed",
        source_review_reference="review-20260910",
        corpus_version="campus-support-v2",
    )


class InMemoryCurrentSupportKnowledgeCorpusTest(TestCase):
    def test_adds_a_new_article_and_increments_revision_once(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        article = _article(
            article_id="network-guide-v1",
            source_content_sha256="sha-network-v1",
        )

        self.assertTrue(corpus.upsert(article))
        self.assertEqual(corpus.revision, 1)
        self.assertEqual(corpus.list_articles(), (article,))
        self.assertFalse(corpus.upsert(article))
        self.assertEqual(corpus.revision, 1)

    def test_rejects_reusing_an_article_id_for_other_content(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(
            (_article(article_id="network-guide-v1", source_content_sha256="sha-v1"),)
        )

        with self.assertRaises(SupportKnowledgeCorpusConflictError):
            corpus.upsert(
                _article(
                    article_id="network-guide-v1",
                    source_content_sha256="sha-v2",
                )
            )

    def test_stores_an_article_and_its_chunks_in_one_revision(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        article = _article(article_id="network-guide-v1", source_content_sha256="sha-v1")
        chunk = SupportKnowledgeChunk(
            "chunk-1", article.article_id, "CampusNet", 1, "html:body", 0, 9, "v2"
        )

        self.assertTrue(corpus.upsert_with_chunks(article, (chunk,)))
        revision, chunks = corpus.chunk_snapshot()
        self.assertEqual(revision, 1)
        self.assertEqual(chunks, (chunk,))
