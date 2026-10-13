from __future__ import annotations

import math

from app.application.support_knowledge_dense_index_preparation import (
    calculate_dense_corpus_fingerprint,
)
from app.application.support_knowledge_chunk_retrieval import (
    SupportKnowledgeChunkSearchHit,
)
from app.domain.dense_support_knowledge_index import (
    DenseSupportKnowledgeIndexSnapshot,
    SupportKnowledgeTextEmbedder,
)
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus


class DenseSupportKnowledgeIndexUnavailableError(RuntimeError):
    """The installed dense index no longer matches the current corpus."""


class DenseSupportKnowledgeChunkRetriever:
    """Searches an already-prepared dense index; it never embeds documents online."""

    def __init__(
        self,
        corpus: CurrentSupportKnowledgeCorpus,
        index: DenseSupportKnowledgeIndexSnapshot,
        embedder: SupportKnowledgeTextEmbedder,
        *,
        vector_store=None,
    ) -> None:
        self._corpus = corpus
        self._index = index
        self._embedder = embedder
        self._vector_store = vector_store

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        if not query.strip():
            raise ValueError("dense support knowledge search query must not be blank")
        if top_k <= 0:
            raise ValueError("dense support knowledge search top_k must be positive")
        chunks = self._verified_current_chunks()
        query_vector = self._embedder.embed_query(query)
        _validate_query_vector(query_vector, self._index.embedding_identity.dimension)
        if self._vector_store is not None:
            ranked = self._vector_store.search(
                query_vector, snapshot=self._index, top_k=top_k
            )
            chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
            if any(key not in chunks_by_id for key, _ in ranked):
                raise DenseSupportKnowledgeIndexUnavailableError("pgvector returned an unknown chunk")
            return tuple(SupportKnowledgeChunkSearchHit(chunk=chunks_by_id[key], score=score)
                         for key, score in ranked)
        vectors_by_chunk_id = {
            vector.chunk_id: vector.values for vector in self._index.vectors
        }
        hits = tuple(
            SupportKnowledgeChunkSearchHit(
                chunk=chunk,
                score=_cosine_similarity(query_vector, vectors_by_chunk_id[chunk.chunk_id]),
            )
            for chunk in chunks
        )
        return tuple(
            sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))[:top_k]
        )

    def _verified_current_chunks(self):
        revision, _articles, chunks = self._corpus.retrieval_snapshot()
        expected_ids = {chunk.chunk_id for chunk in chunks}
        actual_ids = {vector.chunk_id for vector in self._index.vectors}
        if (
            revision != self._index.corpus_revision
            or calculate_dense_corpus_fingerprint(chunks)
            != self._index.corpus_fingerprint
            or self._embedder.embedding_identity != self._index.embedding_identity
            or actual_ids != expected_ids
        ):
            raise DenseSupportKnowledgeIndexUnavailableError(
                "dense index is stale or incompatible; offline preparation is required"
            )
        return chunks


def _validate_query_vector(vector: tuple[float, ...], expected_dimension: int) -> None:
    if len(vector) != expected_dimension:
        raise DenseSupportKnowledgeIndexUnavailableError(
            "query embedding dimension does not match the dense index"
        )
    if not all(math.isfinite(value) for value in vector) or not any(vector):
        raise DenseSupportKnowledgeIndexUnavailableError(
            "query embedding must be finite and non-zero"
        )


def _cosine_similarity(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise DenseSupportKnowledgeIndexUnavailableError(
            "dense index contains a zero vector"
        )
    return numerator / (left_norm * right_norm)
