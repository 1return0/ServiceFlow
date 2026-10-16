from __future__ import annotations

from unittest import TestCase

from app.application.evaluation.retrieval_evaluation import (
    RetrievalEvaluationCase,
    RetrievalEvaluator,
    RetrievalRelevanceJudgment,
)
from app.application.retrieval.support_knowledge_chunk_retrieval import SupportKnowledgeChunkSearchHit
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class RetrievalEvaluatorTest(TestCase):
    def test_reports_recall_mrr_and_ndcg_from_one_frozen_golden_case(self) -> None:
        summary = RetrievalEvaluator().evaluate(
            _StaticRetriever(("chunk-strong", "chunk-noise")),
            (
                RetrievalEvaluationCase(
                    case_id="network-help",
                    query="校园网连不上",
                    judgments=(
                        RetrievalRelevanceJudgment("chunk-strong", 3),
                        RetrievalRelevanceJudgment("chunk-secondary", 1),
                    ),
                ),
            ),
            top_k=2,
        )

        self.assertEqual(0.5, summary.recall_at_k)
        self.assertEqual(1.0, summary.mean_reciprocal_rank)
        self.assertGreater(summary.mean_ndcg_at_k, 0.9)
        self.assertLess(summary.mean_ndcg_at_k, 1.0)


class _StaticRetriever:
    def __init__(self, chunk_ids: tuple[str, ...]) -> None:
        self._chunk_ids = chunk_ids

    def search(self, query: str, *, top_k: int = 3):
        return tuple(
            SupportKnowledgeChunkSearchHit(
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
                score=1.0,
            )
            for chunk_id in self._chunk_ids[:top_k]
        )
