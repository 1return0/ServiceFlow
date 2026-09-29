from __future__ import annotations

from unittest import TestCase

from app.application.refreshable_hybrid_support_knowledge_searcher import (
    RefreshableHybridSupportKnowledgeSearcher,
)
from app.application.reranking_support_knowledge_searcher import (
    RerankingSupportKnowledgeSearcher,
)
from app.application.support_knowledge_chunk_retrieval import SupportKnowledgeChunkSearchHit
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.domain.support_knowledge_reranker import (
    SupportKnowledgeRerankerIdentity,
    SupportKnowledgeRerankResult,
)
from app.infrastructure.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)
from app.infrastructure.qwen_openai_compatible_support_knowledge_reranker import (
    SupportKnowledgeRerankerUnavailableError,
)


class RerankingSupportKnowledgeSearcherTest(TestCase):
    def setUp(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        self.network = _chunk("chunk-network", "校园网络认证", "network")
        self.library = _chunk("chunk-library", "图书馆借阅", "library")
        corpus.upsert_with_chunks(_article("network"), (self.network,))
        corpus.upsert_with_chunks(_article("library"), (self.library,))
        dense = _DenseSearcher((
            SupportKnowledgeChunkSearchHit(self.network, 0.99),
            SupportKnowledgeChunkSearchHit(self.library, 0.98),
        ))
        self.hybrid = RefreshableHybridSupportKnowledgeSearcher(
            corpus,
            dense,
            candidate_k=2,
            rank_constant=0,
        )

    def test_reranks_only_hybrid_candidates(self) -> None:
        result = RerankingSupportKnowledgeSearcher(
            self.hybrid,
            _Reranker((
                SupportKnowledgeRerankResult(1, 0.9),
                SupportKnowledgeRerankResult(0, 0.1),
            )),
            candidate_k=2,
        ).search_with_metadata("校园网络", top_k=1)

        self.assertEqual("library", result.hits[0].article.article_id)
        self.assertEqual("hybrid_reranked", result.metadata.strategy)
        self.assertEqual("applied", result.metadata.reranker_status)
        self.assertEqual(2, result.metadata.candidate_count)

    def test_preserves_hybrid_order_when_reranker_is_unavailable(self) -> None:
        result = RerankingSupportKnowledgeSearcher(
            self.hybrid,
            _UnavailableReranker(),
            candidate_k=2,
        ).search_with_metadata("校园网络", top_k=2)

        self.assertEqual(
            ("network", "library"),
            tuple(hit.article.article_id for hit in result.hits),
        )
        self.assertEqual("hybrid_rerank_degraded", result.metadata.strategy)
        self.assertEqual("degraded", result.metadata.reranker_status)
        self.assertEqual("reranker-model-timeout", result.metadata.reranker_failure_code)


class _DenseSearcher:
    def __init__(self, hits):
        self._hits = hits

    def search(self, query: str, *, top_k: int = 3):
        return self._hits[:top_k]


class _Reranker:
    identity = SupportKnowledgeRerankerIdentity("test", "reranker", "r1")

    def __init__(self, ranks):
        self._ranks = ranks

    def rerank(self, query: str, documents: tuple[str, ...]):
        return self._ranks


class _UnavailableReranker:
    identity = SupportKnowledgeRerankerIdentity("test", "reranker", "r1")

    def rerank(self, query: str, documents: tuple[str, ...]):
        raise SupportKnowledgeRerankerUnavailableError("reranker-model-timeout")


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
