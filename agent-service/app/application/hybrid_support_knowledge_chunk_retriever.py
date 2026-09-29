from __future__ import annotations

from typing import Protocol

from app.application.reciprocal_rank_fusion import reciprocal_rank_fuse
from app.application.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever,
    SupportKnowledgeChunkSearchHit,
)


class SupportKnowledgeChunkRankedSearcher(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        ...


class HybridSupportKnowledgeChunkRetriever:
    """Combines lexical and dense candidate ranks into one evidence-preserving Top-K."""

    def __init__(
        self,
        lexical_retriever: LexicalSupportKnowledgeChunkRetriever,
        dense_retriever: SupportKnowledgeChunkRankedSearcher,
        *,
        candidate_k: int = 20,
        rank_constant: int = 60,
    ) -> None:
        if candidate_k <= 0:
            raise ValueError("hybrid candidate_k must be positive")
        if rank_constant < 0:
            raise ValueError("hybrid rank_constant must not be negative")
        self._lexical_retriever = lexical_retriever
        self._dense_retriever = dense_retriever
        self._candidate_k = candidate_k
        self._rank_constant = rank_constant

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        if top_k <= 0:
            raise ValueError("hybrid support knowledge search top_k must be positive")
        lexical_hits = self._lexical_retriever.search(
            query,
            top_k=self._candidate_k,
        )
        dense_hits = self._dense_retriever.search(
            query,
            top_k=self._candidate_k,
        )
        return reciprocal_rank_fuse(
            (lexical_hits, dense_hits),
            top_k=top_k,
            rank_constant=self._rank_constant,
        )
