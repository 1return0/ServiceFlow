from __future__ import annotations

from unittest import TestCase

from app.application.retrieval.reciprocal_rank_fusion import reciprocal_rank_fuse
from app.application.retrieval.support_knowledge_chunk_retrieval import SupportKnowledgeChunkSearchHit
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class ReciprocalRankFusionTest(TestCase):
    def test_prefers_a_chunk_that_is_highly_ranked_by_both_retrievers(self) -> None:
        lexical = (_hit("chunk-a", 9.0), _hit("chunk-b", 8.0))
        dense = (_hit("chunk-b", 0.95), _hit("chunk-a", 0.92))

        hits = reciprocal_rank_fuse((lexical, dense), top_k=2, rank_constant=0)

        self.assertEqual(("chunk-a", "chunk-b"), tuple(hit.chunk.chunk_id for hit in hits))
        self.assertEqual(1.5, hits[0].score)

    def test_uses_chunk_id_as_a_stable_tie_breaker(self) -> None:
        hits = reciprocal_rank_fuse(
            ((_hit("chunk-b", 1.0),), (_hit("chunk-a", 1.0),)),
            top_k=2,
            rank_constant=0,
        )

        self.assertEqual(("chunk-a", "chunk-b"), tuple(hit.chunk.chunk_id for hit in hits))


def _hit(chunk_id: str, score: float) -> SupportKnowledgeChunkSearchHit:
    return SupportKnowledgeChunkSearchHit(
        SupportKnowledgeChunk(
            chunk_id=chunk_id,
            article_id="network",
            text=chunk_id,
            fragment_ordinal=1,
            fragment_location="paragraph:1",
            fragment_char_start=0,
            fragment_char_end=len(chunk_id),
            chunker_version="test-v1",
        ),
        score,
    )
