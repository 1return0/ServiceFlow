from __future__ import annotations

from typing import Protocol

from app.application.hybrid_support_knowledge_chunk_retriever import HybridSupportKnowledgeChunkRetriever
from app.application.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever,
    SupportKnowledgeChunkSearchHit,
)
from app.application.support_knowledge_retrieval import SupportKnowledgeSearchHit
from app.application.support_knowledge_answering import (
    SupportKnowledgeRetrievalMetadata,
    SupportKnowledgeSearchResult,
    SupportKnowledgeRetrievalTraceStep,
)
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus


class DenseSupportKnowledgeChunkSearcher(Protocol):
    """Structural boundary for an already-prepared online dense searcher."""

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        ...


class RefreshableHybridSupportKnowledgeSearcher:
    """Maps BM25 + Dense RRF chunk hits back to their current source articles."""

    def __init__(
        self,
        corpus: CurrentSupportKnowledgeCorpus,
        dense_searcher: DenseSupportKnowledgeChunkSearcher,
        *,
        candidate_k: int = 20,
        rank_constant: int = 60,
    ) -> None:
        self._corpus = corpus
        self._dense_searcher = dense_searcher
        self._candidate_k = candidate_k
        self._rank_constant = rank_constant
        self._indexed_revision = -1
        self._lexical: LexicalSupportKnowledgeChunkRetriever | None = None
        self._articles_by_id = {}

    def search(self, query: str, *, top_k: int = 3) -> tuple[SupportKnowledgeSearchHit, ...]:
        return self.search_with_metadata(query, top_k=top_k).hits

    def search_with_metadata(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> SupportKnowledgeSearchResult:
        revision, articles, chunks = self._corpus.retrieval_snapshot()
        if self._lexical is None or revision != self._indexed_revision:
            self._lexical = LexicalSupportKnowledgeChunkRetriever(chunks)
            self._articles_by_id = {
                article.article_id: article for article in articles
            }
            self._indexed_revision = revision

        chunk_hits = HybridSupportKnowledgeChunkRetriever(
            self._lexical,
            self._dense_searcher,
            candidate_k=self._candidate_k,
            rank_constant=self._rank_constant,
        ).search(query, top_k=top_k)
        hits = tuple(
            SupportKnowledgeSearchHit(
                article=self._articles_by_id[hit.chunk.article_id],
                score=hit.score,
                evidence_text=hit.chunk.text,
                chunk_id=hit.chunk.chunk_id,
                fragment_location=hit.chunk.fragment_location,
            )
            for hit in chunk_hits
        )
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
