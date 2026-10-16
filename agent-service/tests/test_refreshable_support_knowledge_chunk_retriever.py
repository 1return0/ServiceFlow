from __future__ import annotations

from unittest import TestCase

from app.application.retrieval.refreshable_support_knowledge_chunk_retriever import (
    RefreshableSupportKnowledgeChunkRetriever,
)
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


class RefreshableSupportKnowledgeChunkRetrieverTest(TestCase):
    def test_returns_chunk_text_location_and_parent_article(self) -> None:
        article = SupportKnowledgeArticle(
            "network-v1", "campus_network", "Network", "whole article",
            "https://it.example.edu/network", "official_campus", "sha",
            "reviewed", "review", "v1",
        )
        chunk = SupportKnowledgeChunk(
            "chunk-1", article.article_id, "服务台在A楼", 2,
            "table:2:item:1", 0, 6, "fragment-aware-v2",
        )
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        corpus.upsert_with_chunks(article, (chunk,))

        hit = RefreshableSupportKnowledgeChunkRetriever(corpus).search(
            "服务台在哪", top_k=1
        )[0]

        self.assertEqual(hit.article, article)
        self.assertEqual(hit.retrieved_text, "服务台在A楼")
        self.assertEqual(hit.fragment_location, "table:2:item:1")
