from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DenseEmbeddingIdentity:
    """The exact embedding contract that produced a persisted vector index."""

    provider: str
    model: str
    revision: str
    dimension: int


@dataclass(frozen=True)
class DenseSupportKnowledgeVector:
    chunk_id: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class DenseSupportKnowledgeIndexSnapshot:
    corpus_revision: int
    corpus_fingerprint: str
    embedding_identity: DenseEmbeddingIdentity
    vectors: tuple[DenseSupportKnowledgeVector, ...]


class SupportKnowledgeTextEmbedder(Protocol):
    @property
    def embedding_identity(self) -> DenseEmbeddingIdentity:
        ...

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        ...

    def embed_query(self, text: str) -> tuple[float, ...]:
        ...


class DenseSupportKnowledgeIndexStore(Protocol):
    def load(self) -> DenseSupportKnowledgeIndexSnapshot | None:
        ...

    def save(self, snapshot: DenseSupportKnowledgeIndexSnapshot) -> None:
        ...
