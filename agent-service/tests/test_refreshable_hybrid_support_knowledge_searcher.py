from __future__ import annotations

from unittest import TestCase

from app.application.retrieval.refreshable_hybrid_support_knowledge_searcher import (
    RefreshableHybridSupportKnowledgeSearcher,
)
from app.application.retrieval.support_knowledge_answering import (
    ExtractiveSupportKnowledgeAnswerService,
)
from app.application.retrieval.support_knowledge_chunk_retrieval import (
    SupportKnowledgeChunkSearchHit,
)
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


class RefreshableHybridSupportKnowledgeSearcherTest(TestCase):
    def test_fuses_bm25_and_dense_hits_and_preserves_article_citations(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        network = _chunk("chunk-network", "校园网络认证", "network")
        library = _chunk("chunk-library", "图书馆借阅", "library")
        corpus.upsert_with_chunks(_article("network"), (network,))
        corpus.upsert_with_chunks(_article("library"), (library,))
        dense = _DenseSearcher((
            SupportKnowledgeChunkSearchHit(library, 0.99),
            SupportKnowledgeChunkSearchHit(network, 0.98),
        ))
        searcher = RefreshableHybridSupportKnowledgeSearcher(
            corpus,
            dense,
            candidate_k=2,
            rank_constant=0,
        )

        answer = ExtractiveSupportKnowledgeAnswerService(searcher).answer(
            "校园网络认证",
            top_k=2,
        )

        self.assertEqual("hybrid", answer.retrieval_strategy)
        self.assertEqual("network", answer.citations[0].article_id)
        self.assertEqual("chunk-network", answer.citations[0].chunk_id)
        self.assertEqual(1, dense.search_calls)


class _DenseSearcher:
    def __init__(self, hits: tuple[SupportKnowledgeChunkSearchHit, ...]) -> None:
        self._hits = hits
        self.search_calls = 0

    def search(self, query: str, *, top_k: int = 3):
        self.search_calls += 1
        return self._hits[:top_k]


def _article(article_id: str) -> SupportKnowledgeArticle:
    return SupportKnowledgeArticle(
        article_id=article_id,
        category="campus_network",
        title=article_id,
        content=article_id,
        source_reference=f"https://it.example.edu/{article_id}",
        source_kind="official_campus",
        source_content_sha256="a" * 64,
        source_review_status="reviewed",
        source_review_reference="review-1",
        corpus_version="v1",
    )


def _chunk(chunk_id: str, text: str, article_id: str) -> SupportKnowledgeChunk:
    return SupportKnowledgeChunk(
        chunk_id=chunk_id,
        article_id=article_id,
        text=text,
        fragment_ordinal=1,
        fragment_location="paragraph:1",
        fragment_char_start=0,
        fragment_char_end=len(text),
        chunker_version="test-v1",
    )
