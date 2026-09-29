from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from app.application.support_knowledge_chunk_retrieval import (
    SupportKnowledgeChunkSearchHit,
)


@dataclass(frozen=True)
class RetrievalRelevanceJudgment:
    chunk_id: str
    relevance_grade: int

    def __post_init__(self) -> None:
        if self.relevance_grade < 1:
            raise ValueError("retrieval relevance grade must be at least one")


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    case_id: str
    query: str
    judgments: tuple[RetrievalRelevanceJudgment, ...]

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("retrieval evaluation query must not be blank")
        if not self.judgments:
            raise ValueError("retrieval evaluation case needs at least one judgment")
        if len({judgment.chunk_id for judgment in self.judgments}) != len(self.judgments):
            raise ValueError("retrieval evaluation judgments must have unique chunk IDs")


class SupportKnowledgeChunkSearcher(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        ...


@dataclass(frozen=True)
class RetrievalEvaluationCaseResult:
    case_id: str
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    retrieved_chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluationSummary:
    top_k: int
    total_cases: int
    recall_at_k: float
    mean_reciprocal_rank: float
    mean_ndcg_at_k: float
    cases: tuple[RetrievalEvaluationCaseResult, ...]


class RetrievalEvaluator:
    def evaluate(
        self,
        retriever: SupportKnowledgeChunkSearcher,
        cases: tuple[RetrievalEvaluationCase, ...],
        *,
        top_k: int,
    ) -> RetrievalEvaluationSummary:
        if not cases:
            raise ValueError("retrieval evaluation requires at least one case")
        if top_k <= 0:
            raise ValueError("retrieval evaluation top_k must be positive")
        results = tuple(
            self._evaluate_case(retriever, case, top_k=top_k) for case in cases
        )
        return RetrievalEvaluationSummary(
            top_k=top_k,
            total_cases=len(results),
            recall_at_k=sum(result.recall_at_k for result in results) / len(results),
            mean_reciprocal_rank=(
                sum(result.reciprocal_rank for result in results) / len(results)
            ),
            mean_ndcg_at_k=sum(result.ndcg_at_k for result in results) / len(results),
            cases=results,
        )

    @staticmethod
    def _evaluate_case(
        retriever: SupportKnowledgeChunkSearcher,
        case: RetrievalEvaluationCase,
        *,
        top_k: int,
    ) -> RetrievalEvaluationCaseResult:
        hits = retriever.search(case.query, top_k=top_k)
        retrieved_ids = tuple(hit.chunk.chunk_id for hit in hits)
        grades_by_id = {
            judgment.chunk_id: judgment.relevance_grade for judgment in case.judgments
        }
        relevant_ids = set(grades_by_id)
        recalled = sum(chunk_id in relevant_ids for chunk_id in retrieved_ids)
        first_relevant_rank = next(
            (
                rank
                for rank, chunk_id in enumerate(retrieved_ids, start=1)
                if chunk_id in relevant_ids
            ),
            None,
        )
        return RetrievalEvaluationCaseResult(
            case_id=case.case_id,
            recall_at_k=recalled / len(relevant_ids),
            reciprocal_rank=(1.0 / first_relevant_rank if first_relevant_rank else 0.0),
            ndcg_at_k=_ndcg_at_k(retrieved_ids, grades_by_id, top_k=top_k),
            retrieved_chunk_ids=retrieved_ids,
        )


def _ndcg_at_k(
    retrieved_ids: tuple[str, ...],
    grades_by_id: dict[str, int],
    *,
    top_k: int,
) -> float:
    def discounted_gain(grade: int, rank: int) -> float:
        return (2**grade - 1) / math.log2(rank + 1)

    actual = sum(
        discounted_gain(grades_by_id.get(chunk_id, 0), rank)
        for rank, chunk_id in enumerate(retrieved_ids[:top_k], start=1)
    )
    ideal = sum(
        discounted_gain(grade, rank)
        for rank, grade in enumerate(
            sorted(grades_by_id.values(), reverse=True)[:top_k],
            start=1,
        )
    )
    return actual / ideal if ideal else 0.0
