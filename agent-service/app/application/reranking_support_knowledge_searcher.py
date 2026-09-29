from __future__ import annotations

from app.application.support_knowledge_answering import (
    SupportKnowledgeRetrievalMetadata,
    SupportKnowledgeSearchResult,
    SupportKnowledgeRetrievalTraceStep,
)
from app.application.refreshable_hybrid_support_knowledge_searcher import (
    RefreshableHybridSupportKnowledgeSearcher,
)
from app.domain.support_knowledge_reranker import SupportKnowledgeReranker
from app.infrastructure.qwen_openai_compatible_support_knowledge_reranker import (
    SupportKnowledgeRerankerUnavailableError,
)


class RerankingSupportKnowledgeSearcher:
    """Reranks only Hybrid candidates and preserves Hybrid order on provider failure."""

    def __init__(
        self,
        hybrid_searcher: RefreshableHybridSupportKnowledgeSearcher,
        reranker: SupportKnowledgeReranker,
        *,
        candidate_k: int = 10,
    ) -> None:
        if candidate_k <= 0:
            raise ValueError("reranker candidate_k must be positive")
        self._hybrid_searcher = hybrid_searcher
        self._reranker = reranker
        self._candidate_k = candidate_k

    def search(self, query: str, *, top_k: int = 3):
        return self.search_with_metadata(query, top_k=top_k).hits

    def search_with_metadata(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> SupportKnowledgeSearchResult:
        hybrid_result = self._hybrid_searcher.search_with_metadata(
            query,
            top_k=self._candidate_k,
        )
        candidates = hybrid_result.hits
        if not candidates:
            return SupportKnowledgeSearchResult(
                hits=(),
                metadata=SupportKnowledgeRetrievalMetadata(
                    strategy="hybrid_reranked",
                    candidate_count=0,
                    reranker_status="applied",
                    reranker_identity=_identity_text(self._reranker),
                    trace_steps=hybrid_result.metadata.trace_steps + (
                        SupportKnowledgeRetrievalTraceStep("rerank", "applied"),
                    ),
                ),
            )
        try:
            ranks = self._reranker.rerank(
                query,
                tuple(hit.retrieved_text for hit in candidates),
            )
        except SupportKnowledgeRerankerUnavailableError as error:
            return SupportKnowledgeSearchResult(
                hits=candidates[:top_k],
                metadata=SupportKnowledgeRetrievalMetadata(
                    strategy="hybrid_rerank_degraded",
                    candidate_count=len(candidates),
                    reranker_status="degraded",
                    reranker_identity=_identity_text(self._reranker),
                    reranker_failure_code=error.failure_code,
                    trace_steps=hybrid_result.metadata.trace_steps + (
                        SupportKnowledgeRetrievalTraceStep("rerank", "degraded"),
                    ),
                ),
            )
        ordered_hits = tuple(
            candidates[result.candidate_index]
            for result in sorted(
                ranks,
                key=lambda result: (-result.relevance_score, result.candidate_index),
            )
        )
        return SupportKnowledgeSearchResult(
            hits=ordered_hits[:top_k],
            metadata=SupportKnowledgeRetrievalMetadata(
                strategy="hybrid_reranked",
                candidate_count=len(candidates),
                reranker_status="applied",
                reranker_identity=_identity_text(self._reranker),
                trace_steps=hybrid_result.metadata.trace_steps + (
                    SupportKnowledgeRetrievalTraceStep("rerank", "applied"),
                ),
            ),
        )

    def close(self) -> None:
        close = getattr(self._reranker, "close", None)
        if callable(close):
            close()


def _identity_text(reranker: SupportKnowledgeReranker) -> str:
    identity = reranker.identity
    return f"{identity.provider}:{identity.model}:{identity.revision}"
