from __future__ import annotations

from app.application.retrieval.support_knowledge_chunk_retrieval import (
    SupportKnowledgeChunkSearchHit,
)


def reciprocal_rank_fuse(
    ranked_result_sets: tuple[tuple[SupportKnowledgeChunkSearchHit, ...], ...],
    *,
    top_k: int,
    rank_constant: int = 60,
) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
    """Fuse rank lists without comparing incompatible BM25 and cosine scores."""
    if top_k <= 0:
        raise ValueError("RRF top_k must be positive")
    if rank_constant < 0:
        raise ValueError("RRF rank_constant must not be negative")
    scores_by_chunk_id: dict[str, float] = {}
    chunks_by_id = {}
    for result_set in ranked_result_sets:
        for rank, hit in enumerate(result_set, start=1):
            chunk_id = hit.chunk.chunk_id
            chunks_by_id[chunk_id] = hit.chunk
            scores_by_chunk_id[chunk_id] = scores_by_chunk_id.get(chunk_id, 0.0) + (
                1.0 / (rank_constant + rank)
            )
    return tuple(
        SupportKnowledgeChunkSearchHit(chunks_by_id[chunk_id], score)
        for chunk_id, score in sorted(
            scores_by_chunk_id.items(),
            key=lambda item: (-item[1], item[0]),
        )[:top_k]
    )
