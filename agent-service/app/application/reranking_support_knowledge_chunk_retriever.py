from __future__ import annotations

from app.application.hybrid_support_knowledge_chunk_retriever import (
    HybridSupportKnowledgeChunkRetriever,
)
from app.application.support_knowledge_chunk_retrieval import (
    SupportKnowledgeChunkSearchHit,
)
from app.domain.support_knowledge_reranker import SupportKnowledgeReranker
from app.infrastructure.qwen_openai_compatible_support_knowledge_reranker import (
    SupportKnowledgeRerankerUnavailableError,
)


class RerankingSupportKnowledgeChunkRetriever:
    """Evaluation-facing exact-Chunk reranker; provider failure preserves Hybrid order."""

    def __init__(
        self,
        hybrid_retriever: HybridSupportKnowledgeChunkRetriever,
        reranker: SupportKnowledgeReranker,
        *,
        candidate_k: int = 10,
        allow_degraded: bool = False,
    ) -> None:
        if candidate_k <= 0:
            raise ValueError("reranker candidate_k must be positive")
        self._hybrid_retriever = hybrid_retriever
        self._reranker = reranker
        self._candidate_k = candidate_k
        self._allow_degraded = allow_degraded

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        candidates = self._hybrid_retriever.search(query, top_k=self._candidate_k)
        if not candidates:
            return ()
        try:
            ranks = self._reranker.rerank(
                query,
                tuple(hit.chunk.text for hit in candidates),
            )
        except SupportKnowledgeRerankerUnavailableError:
            if not self._allow_degraded:
                # An experiment labelled "hybrid_rerank" must not silently become
                # a Hybrid-only run merely because the model call failed.
                raise
            return candidates[:top_k]
        return tuple(
            candidates[result.candidate_index]
            for result in sorted(
                ranks,
                key=lambda result: (-result.relevance_score, result.candidate_index),
            )
        )[:top_k]
