from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.application.support_knowledge_retrieval import (
    SupportKnowledgeSearchHit,
)


class SupportKnowledgeSearcher(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeSearchHit, ...]:
        ...


@dataclass(frozen=True)
class SupportKnowledgeRetrievalTraceStep:
    stage: str
    status: Literal["completed", "applied", "degraded", "refused"]


@dataclass(frozen=True)
class SupportKnowledgeRetrievalMetadata:
    strategy: Literal["lexical", "hybrid", "hybrid_reranked", "hybrid_rerank_degraded"]
    candidate_count: int
    reranker_status: Literal["not_configured", "applied", "degraded"]
    reranker_identity: str | None = None
    reranker_failure_code: str | None = None
    initial_evidence_count: int | None = None
    secondary_search_attempted: bool = False
    secondary_search_reason: str | None = None
    query_rewrite_attempted: bool = False
    query_rewrite_status: Literal["not_requested", "applied", "degraded"] = "not_requested"
    query_rewriter_identity: str | None = None
    query_rewrite_failure_code: str | None = None
    trace_steps: tuple[SupportKnowledgeRetrievalTraceStep, ...] = ()


@dataclass(frozen=True)
class SupportKnowledgeSearchResult:
    hits: tuple[SupportKnowledgeSearchHit, ...]
    metadata: SupportKnowledgeRetrievalMetadata


class SupportKnowledgeAnswerProvider(Protocol):
    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        ...


@dataclass(frozen=True)
class SupportKnowledgeCitation:
    article_id: str
    title: str
    source_reference: str
    chunk_id: str | None = None
    fragment_location: str | None = None


@dataclass(frozen=True)
class SupportKnowledgeAnswer:
    status: Literal["answered", "insufficient_evidence"]
    answer_text: str
    citations: tuple[SupportKnowledgeCitation, ...]
    model_called: bool = False
    model_identity: str | None = None
    retrieval_strategy: Literal[
        "lexical", "hybrid", "hybrid_reranked", "hybrid_rerank_degraded"
    ] = "lexical"
    reranker_status: Literal["not_configured", "applied", "degraded"] = "not_configured"
    reranker_identity: str | None = None
    reranker_failure_code: str | None = None
    initial_evidence_count: int | None = None
    secondary_search_attempted: bool = False
    secondary_search_reason: str | None = None
    query_rewrite_attempted: bool = False
    query_rewrite_status: Literal["not_requested", "applied", "degraded"] = "not_requested"
    query_rewriter_identity: str | None = None
    query_rewrite_failure_code: str | None = None
    retrieval_trace: tuple[SupportKnowledgeRetrievalTraceStep, ...] = ()


class ExtractiveSupportKnowledgeAnswerService:
    """Answers only with retrieved article content until LLM synthesis is added."""

    def __init__(self, searcher: SupportKnowledgeSearcher) -> None:
        self._searcher = searcher

    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        search_result = _search_with_metadata(self._searcher, question, top_k=top_k)
        hits = search_result.hits
        metadata = search_result.metadata
        if not hits:
            return SupportKnowledgeAnswer(
                status="insufficient_evidence",
                answer_text=(
                    "当前知识库没有检索到足够依据，请补充问题场景或转人工服务。"
                ),
                citations=(),
                retrieval_strategy=metadata.strategy,
                reranker_status=metadata.reranker_status,
                reranker_identity=metadata.reranker_identity,
                reranker_failure_code=metadata.reranker_failure_code,
                initial_evidence_count=metadata.initial_evidence_count,
                secondary_search_attempted=metadata.secondary_search_attempted,
                secondary_search_reason=metadata.secondary_search_reason,
                query_rewrite_attempted=metadata.query_rewrite_attempted,
                query_rewrite_status=metadata.query_rewrite_status,
                query_rewriter_identity=metadata.query_rewriter_identity,
                query_rewrite_failure_code=metadata.query_rewrite_failure_code,
                retrieval_trace=metadata.trace_steps + (
                    SupportKnowledgeRetrievalTraceStep(
                        "refusal_insufficient_evidence",
                        "refused",
                    ),
                ),
            )

        primary_hit = hits[0]
        return SupportKnowledgeAnswer(
            status="answered",
            answer_text=(
                f"根据《{primary_hit.article.title}》："
                f"{primary_hit.retrieved_text}"
            ),
            citations=(_to_citation(primary_hit),),
            retrieval_strategy=metadata.strategy,
            reranker_status=metadata.reranker_status,
            reranker_identity=metadata.reranker_identity,
            reranker_failure_code=metadata.reranker_failure_code,
            initial_evidence_count=metadata.initial_evidence_count,
            secondary_search_attempted=metadata.secondary_search_attempted,
            secondary_search_reason=metadata.secondary_search_reason,
            query_rewrite_attempted=metadata.query_rewrite_attempted,
            query_rewrite_status=metadata.query_rewrite_status,
            query_rewriter_identity=metadata.query_rewriter_identity,
            query_rewrite_failure_code=metadata.query_rewrite_failure_code,
            retrieval_trace=metadata.trace_steps + (
                SupportKnowledgeRetrievalTraceStep("answer_from_evidence", "completed"),
            ),
        )

    def close(self) -> None:
        close = getattr(self._searcher, "close", None)
        if callable(close):
            close()


def _to_citation(hit: SupportKnowledgeSearchHit) -> SupportKnowledgeCitation:
    return SupportKnowledgeCitation(
        article_id=hit.article.article_id,
        title=hit.article.title,
        source_reference=hit.article.source_reference,
        chunk_id=hit.chunk_id,
        fragment_location=hit.fragment_location,
    )


def _search_with_metadata(
    searcher: SupportKnowledgeSearcher,
    question: str,
    *,
    top_k: int,
) -> SupportKnowledgeSearchResult:
    search_with_metadata = getattr(searcher, "search_with_metadata", None)
    if callable(search_with_metadata):
        return search_with_metadata(question, top_k=top_k)
    hits = searcher.search(question, top_k=top_k)
    return SupportKnowledgeSearchResult(
        hits=hits,
        metadata=SupportKnowledgeRetrievalMetadata(
            strategy="lexical",
            candidate_count=len(hits),
            reranker_status="not_configured",
            trace_steps=(
                SupportKnowledgeRetrievalTraceStep("lexical_retrieval", "completed"),
            ),
        ),
    )
