from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from app.domain.dense_support_knowledge_index import (
    DenseSupportKnowledgeIndexSnapshot,
    DenseSupportKnowledgeIndexStore,
    DenseSupportKnowledgeVector,
    SupportKnowledgeTextEmbedder,
)
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class DenseSupportKnowledgeIndexBuildError(RuntimeError):
    """An embedding result cannot safely become a persistent index."""


@dataclass(frozen=True)
class DenseSupportKnowledgeIndexPreparationResult:
    snapshot: DenseSupportKnowledgeIndexSnapshot
    reused_existing_index: bool


class SupportKnowledgeDenseIndexPreparationService:
    """Builds document vectors offline and reuses only an exact compatible index."""

    def __init__(
        self,
        corpus: CurrentSupportKnowledgeCorpus,
        embedder: SupportKnowledgeTextEmbedder,
        store: DenseSupportKnowledgeIndexStore,
    ) -> None:
        self._corpus = corpus
        self._embedder = embedder
        self._store = store

    def prepare(self) -> DenseSupportKnowledgeIndexPreparationResult:
        corpus_revision, _articles, chunks = self._corpus.retrieval_snapshot()
        corpus_fingerprint = calculate_dense_corpus_fingerprint(chunks)
        identity = self._embedder.embedding_identity
        existing = self._store.load()
        if (
            existing is not None
            and existing.corpus_revision == corpus_revision
            and existing.corpus_fingerprint == corpus_fingerprint
            and existing.embedding_identity == identity
        ):
            return DenseSupportKnowledgeIndexPreparationResult(existing, True)

        vectors = self._embedder.embed_documents(
            tuple(chunk.text for chunk in chunks)
        )
        _validate_vectors(vectors, chunks, expected_dimension=identity.dimension)
        snapshot = DenseSupportKnowledgeIndexSnapshot(
            corpus_revision=corpus_revision,
            corpus_fingerprint=corpus_fingerprint,
            embedding_identity=identity,
            vectors=tuple(
                DenseSupportKnowledgeVector(chunk.chunk_id, vector)
                for chunk, vector in zip(chunks, vectors, strict=True)
            ),
        )
        self._store.save(snapshot)
        return DenseSupportKnowledgeIndexPreparationResult(snapshot, False)


def calculate_dense_corpus_fingerprint(
    chunks: tuple[SupportKnowledgeChunk, ...],
) -> str:
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "article_id": chunk.article_id,
            "text": chunk.text,
            "fragment_location": chunk.fragment_location,
            "chunker_version": chunk.chunker_version,
        }
        for chunk in chunks
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_vectors(
    vectors: tuple[tuple[float, ...], ...],
    chunks: tuple[SupportKnowledgeChunk, ...],
    *,
    expected_dimension: int,
) -> None:
    if len(vectors) != len(chunks):
        raise DenseSupportKnowledgeIndexBuildError(
            "embedding result count does not match corpus chunk count"
        )
    if expected_dimension <= 0:
        raise DenseSupportKnowledgeIndexBuildError(
            "embedding identity dimension must be positive"
        )
    for vector in vectors:
        if len(vector) != expected_dimension:
            raise DenseSupportKnowledgeIndexBuildError(
                "embedding result dimension does not match embedding identity"
            )
        if not all(math.isfinite(value) for value in vector):
            raise DenseSupportKnowledgeIndexBuildError(
                "embedding result must contain only finite values"
            )
        if not any(value != 0.0 for value in vector):
            raise DenseSupportKnowledgeIndexBuildError(
                "embedding result must not be an all-zero vector"
            )
