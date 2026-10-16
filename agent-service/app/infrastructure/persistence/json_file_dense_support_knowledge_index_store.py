from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.domain.dense_support_knowledge_index import (
    DenseEmbeddingIdentity,
    DenseSupportKnowledgeIndexSnapshot,
    DenseSupportKnowledgeVector,
)


class DenseSupportKnowledgeIndexPersistenceError(RuntimeError):
    """A persisted dense index cannot safely be read or written."""


class _StoredEmbeddingIdentity(BaseModel):
    provider: str
    model: str
    revision: str
    dimension: int


class _StoredVector(BaseModel):
    chunk_id: str
    values: list[float]


class _StoredDenseIndex(BaseModel):
    schema_version: int = Field(1, ge=1)
    corpus_revision: int = Field(ge=0)
    corpus_fingerprint: str
    embedding_identity: _StoredEmbeddingIdentity
    vectors: list[_StoredVector]


class JsonFileDenseSupportKnowledgeIndexStore:
    """Small single-process durable store for an offline dense index snapshot."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> DenseSupportKnowledgeIndexSnapshot | None:
        if not self._path.exists():
            return None
        try:
            stored = _StoredDenseIndex.model_validate_json(
                self._path.read_text(encoding="utf-8")
            )
            if stored.schema_version != 1:
                raise ValueError("unsupported dense index schema version")
            return DenseSupportKnowledgeIndexSnapshot(
                corpus_revision=stored.corpus_revision,
                corpus_fingerprint=stored.corpus_fingerprint,
                embedding_identity=DenseEmbeddingIdentity(
                    **stored.embedding_identity.model_dump()
                ),
                vectors=tuple(
                    DenseSupportKnowledgeVector(
                        chunk_id=row.chunk_id,
                        values=tuple(row.values),
                    )
                    for row in stored.vectors
                ),
            )
        except (OSError, ValueError, ValidationError, json.JSONDecodeError) as error:
            raise DenseSupportKnowledgeIndexPersistenceError(
                "dense support knowledge index could not be loaded"
            ) from error

    def save(self, snapshot: DenseSupportKnowledgeIndexSnapshot) -> None:
        payload = {
            "schema_version": 1,
            "corpus_revision": snapshot.corpus_revision,
            "corpus_fingerprint": snapshot.corpus_fingerprint,
            "embedding_identity": {
                "provider": snapshot.embedding_identity.provider,
                "model": snapshot.embedding_identity.model,
                "revision": snapshot.embedding_identity.revision,
                "dimension": snapshot.embedding_identity.dimension,
            },
            "vectors": [
                {"chunk_id": vector.chunk_id, "values": list(vector.values)}
                for vector in snapshot.vectors
            ],
        }
        temporary_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            temporary_path.replace(self._path)
        except OSError as error:
            raise DenseSupportKnowledgeIndexPersistenceError(
                "dense support knowledge index could not be saved"
            ) from error
