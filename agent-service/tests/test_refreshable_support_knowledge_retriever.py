from __future__ import annotations

from unittest import TestCase

from app.application.retrieval.refreshable_support_knowledge_retriever import (
    RefreshableLexicalSupportKnowledgeRetriever,
)
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


def _article() -> SupportKnowledgeArticle:
    return SupportKnowledgeArticle(
        article_id="network-guide-v1",
        category="campus_network",
        title="Campus network guide",
        content="Connect to CampusNet before class.",
        source_reference="https://it.example.edu/network-guide.html",
        source_kind="official_campus",
        source_content_sha256="sha-network-v1",
        source_review_status="reviewed",
        source_review_reference="review-20260910",
        corpus_version="campus-support-v2",
    )


class RefreshableSupportKnowledgeRetrieverTest(TestCase):
    def test_rebuilds_its_index_after_a_current_corpus_change(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        retriever = RefreshableLexicalSupportKnowledgeRetriever(corpus)

        self.assertEqual(retriever.search("CampusNet"), ())
        self.assertEqual(retriever.indexed_revision, 0)
        corpus.upsert(_article())

        hits = retriever.search("CampusNet")

        self.assertEqual(hits[0].article.article_id, "network-guide-v1")
        self.assertEqual(retriever.indexed_revision, 1)
