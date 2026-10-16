from __future__ import annotations

from unittest import TestCase

from app.application.retrieval.controlled_secondary_support_knowledge_searcher import (
    ControlledSecondarySupportKnowledgeSearcher,
)
from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeRetrievalMetadata,
    SupportKnowledgeSearchResult,
    SupportKnowledgeRetrievalTraceStep,
)
from app.application.retrieval.support_knowledge_retrieval import SupportKnowledgeSearchHit
from app.application.retrieval.model_support_knowledge_query_rewriter import (
    SupportKnowledgeQueryRewriteUnavailableError,
)
from app.domain.support_knowledge import SupportKnowledgeArticle


class ControlledSecondarySupportKnowledgeSearcherTest(TestCase):
    def test_runs_exactly_one_wider_search_only_when_initial_evidence_is_insufficient(self) -> None:
        searcher = _Searcher(initial_count=1)
        result = ControlledSecondarySupportKnowledgeSearcher(
            searcher,
            minimum_evidence_count=2,
            secondary_top_k=6,
        ).search_with_metadata("校园网络", top_k=3)

        self.assertEqual((3, 6), tuple(searcher.requested_top_ks))
        self.assertEqual(3, len(result.hits))
        self.assertTrue(result.metadata.secondary_search_attempted)
        self.assertEqual(1, result.metadata.initial_evidence_count)
        self.assertEqual("insufficient-initial-evidence", result.metadata.secondary_search_reason)
        self.assertEqual(
            (
                "initial_hybrid_retrieval",
                "initial_evidence_gate",
                "secondary_hybrid_retrieval",
                "secondary_retrieval",
            ),
            tuple(step.stage for step in result.metadata.trace_steps),
        )

    def test_does_not_run_secondary_search_when_initial_evidence_reaches_threshold(self) -> None:
        searcher = _Searcher(initial_count=2)
        result = ControlledSecondarySupportKnowledgeSearcher(
            searcher,
            minimum_evidence_count=2,
            secondary_top_k=6,
        ).search_with_metadata("校园网络", top_k=3)

        self.assertEqual((3,), tuple(searcher.requested_top_ks))
        self.assertFalse(result.metadata.secondary_search_attempted)
        self.assertEqual(2, result.metadata.initial_evidence_count)
        self.assertEqual(
            ("initial_hybrid_retrieval", "initial_evidence_gate"),
            tuple(step.stage for step in result.metadata.trace_steps),
        )

    def test_rewrites_only_the_one_secondary_query(self) -> None:
        searcher = _Searcher(initial_count=1)
        result = ControlledSecondarySupportKnowledgeSearcher(
            searcher,
            minimum_evidence_count=2,
            secondary_top_k=6,
            query_rewriter=_Rewriter("校园网认证失败处理"),
        ).search_with_metadata("校园网连不上", top_k=3)

        self.assertEqual(("校园网连不上", "校园网认证失败处理"), tuple(searcher.queries))
        self.assertTrue(result.metadata.query_rewrite_attempted)
        self.assertEqual("applied", result.metadata.query_rewrite_status)
        self.assertEqual("test:rewrite-v1", result.metadata.query_rewriter_identity)

    def test_keeps_the_original_query_when_rewriter_is_unavailable(self) -> None:
        searcher = _Searcher(initial_count=1)
        result = ControlledSecondarySupportKnowledgeSearcher(
            searcher,
            minimum_evidence_count=2,
            secondary_top_k=6,
            query_rewriter=_UnavailableRewriter(),
        ).search_with_metadata("校园网连不上", top_k=3)

        self.assertEqual(("校园网连不上", "校园网连不上"), tuple(searcher.queries))
        self.assertEqual("degraded", result.metadata.query_rewrite_status)
        self.assertEqual(
            "query-rewriter-model-timeout",
            result.metadata.query_rewrite_failure_code,
        )


class _Searcher:
    def __init__(self, *, initial_count: int) -> None:
        self._initial_count = initial_count
        self.requested_top_ks: list[int] = []
        self.queries: list[str] = []

    def search_with_metadata(self, query: str, *, top_k: int):
        self.requested_top_ks.append(top_k)
        self.queries.append(query)
        count = self._initial_count if len(self.requested_top_ks) == 1 else 3
        hits = tuple(_hit(index) for index in range(min(top_k, count)))
        return SupportKnowledgeSearchResult(
            hits=hits,
            metadata=SupportKnowledgeRetrievalMetadata(
                strategy="hybrid",
                candidate_count=len(hits),
                reranker_status="not_configured",
                trace_steps=(
                    SupportKnowledgeRetrievalTraceStep("hybrid_retrieval", "completed"),
                ),
            ),
        )

    def search(self, query: str, *, top_k: int):
        return self.search_with_metadata(query, top_k=top_k).hits


def _hit(index: int) -> SupportKnowledgeSearchHit:
    article = SupportKnowledgeArticle(
        article_id=f"article-{index}",
        category="campus_network",
        title=f"Title {index}",
        content=f"Text {index}",
        source_reference=f"https://it.example.edu/{index}",
        source_kind="official_campus",
        source_content_sha256="a" * 64,
        source_review_status="reviewed",
        source_review_reference="review-1",
        corpus_version="v1",
    )
    return SupportKnowledgeSearchHit(article, score=float(3 - index), chunk_id=f"chunk-{index}")


class _Rewriter:
    identity = "test:rewrite-v1"

    def __init__(self, rewritten: str) -> None:
        self._rewritten = rewritten

    def rewrite(self, query: str) -> str:
        return self._rewritten


class _UnavailableRewriter:
    identity = "test:rewrite-v1"

    def rewrite(self, query: str) -> str:
        raise SupportKnowledgeQueryRewriteUnavailableError("query-rewriter-model-timeout")
