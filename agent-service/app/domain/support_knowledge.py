from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


SupportKnowledgeCategory = Literal[
    "account",
    "campus_network",
    "teaching_system",
    "classroom_equipment",
    "service_process",
]

SupportKnowledgeSourceKind = Literal["official_campus", "demonstration"]
SupportKnowledgeSourceReviewStatus = Literal["reviewed", "demonstration"]


@dataclass(frozen=True)
class SupportKnowledgeArticle:
    article_id: str
    category: SupportKnowledgeCategory
    title: str
    content: str
    source_reference: str
    source_kind: SupportKnowledgeSourceKind
    source_content_sha256: str
    source_review_status: SupportKnowledgeSourceReviewStatus
    source_review_reference: str
    corpus_version: str


@dataclass(frozen=True)
class SupportKnowledgeArticleMetadata:
    """Human-reviewed fields that parsing alone cannot infer safely."""

    article_id: str
    category: SupportKnowledgeCategory
    fallback_title: str
    source_reference: str
    source_kind: SupportKnowledgeSourceKind
    source_review_status: SupportKnowledgeSourceReviewStatus
    source_review_reference: str
    corpus_version: str


class SupportKnowledgeCatalog(Protocol):
    def list_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        ...


class CurrentSupportKnowledgeCorpus(SupportKnowledgeCatalog, Protocol):
    @property
    def revision(self) -> int:
        ...

    def upsert(self, article: SupportKnowledgeArticle) -> bool:
        """Returns True only when the current corpus changed."""
        ...

    def snapshot(self) -> tuple[int, tuple[SupportKnowledgeArticle, ...]]:
        """Returns a self-consistent corpus revision and article set."""
        ...

    def upsert_with_chunks(
        self,
        article: SupportKnowledgeArticle,
        chunks: tuple[SupportKnowledgeChunk, ...],
    ) -> bool:
        ...

    def chunk_snapshot(self) -> tuple[int, tuple[SupportKnowledgeChunk, ...]]:
        ...

    def retrieval_snapshot(
        self,
    ) -> tuple[
        int,
        tuple[SupportKnowledgeArticle, ...],
        tuple[SupportKnowledgeChunk, ...],
    ]:
        ...
