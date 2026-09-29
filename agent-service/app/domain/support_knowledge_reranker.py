from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SupportKnowledgeRerankerIdentity:
    provider: str
    model: str
    revision: str


@dataclass(frozen=True)
class SupportKnowledgeRerankResult:
    candidate_index: int
    relevance_score: float


class SupportKnowledgeReranker(Protocol):
    @property
    def identity(self) -> SupportKnowledgeRerankerIdentity:
        ...

    def rerank(
        self,
        query: str,
        documents: tuple[str, ...],
    ) -> tuple[SupportKnowledgeRerankResult, ...]:
        ...
