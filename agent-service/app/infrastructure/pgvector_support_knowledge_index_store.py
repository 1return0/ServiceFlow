from __future__ import annotations

from dataclasses import asdict

from app.domain.dense_support_knowledge_index import (
    DenseEmbeddingIdentity, DenseSupportKnowledgeIndexSnapshot,
    DenseSupportKnowledgeVector,
)
from app.infrastructure.pgvector_index import PgvectorIndex, PgvectorIndexUnavailableError
from app.application.dense_support_knowledge_chunk_retrieval import DenseSupportKnowledgeIndexUnavailableError


class PgvectorSupportKnowledgeIndexStore:
    """Persists offline vectors and executes online cosine ranking in PostgreSQL."""

    def __init__(self, dsn: str, *, index_name: str = "serviceflow-public-knowledge") -> None:
        self._index = PgvectorIndex(dsn, index_name=index_name)
        self._index.setup()

    @staticmethod
    def _metadata(snapshot):
        return {"corpus_revision": snapshot.corpus_revision,
                "corpus_fingerprint": snapshot.corpus_fingerprint,
                "embedding_identity": asdict(snapshot.embedding_identity)}

    def load(self) -> DenseSupportKnowledgeIndexSnapshot | None:
        stored = self._index.load()
        if stored is None:
            return None
        metadata, vectors, dimension, _snapshot_id = stored
        identity = DenseEmbeddingIdentity(**metadata["embedding_identity"])
        if identity.dimension != dimension:
            raise ValueError("pgvector embedding metadata dimension mismatch")
        return DenseSupportKnowledgeIndexSnapshot(
            metadata["corpus_revision"], metadata["corpus_fingerprint"], identity,
            tuple(DenseSupportKnowledgeVector(key, values) for key, values in vectors),
        )

    def save(self, snapshot: DenseSupportKnowledgeIndexSnapshot) -> None:
        self._index.save(self._metadata(snapshot),
            ((vector.chunk_id, vector.values) for vector in snapshot.vectors),
            snapshot.embedding_identity.dimension)

    def search(self, query_vector, *, snapshot, top_k):
        snapshot_id = self._index.snapshot_id(self._metadata(snapshot),
            ((vector.chunk_id, vector.values) for vector in snapshot.vectors),
            snapshot.embedding_identity.dimension)
        try:
            return self._index.search(query_vector,
                dimension=snapshot.embedding_identity.dimension,
                snapshot_id=snapshot_id, top_k=top_k)
        except PgvectorIndexUnavailableError as error:
            raise DenseSupportKnowledgeIndexUnavailableError(
                "pgvector knowledge index is unavailable or stale"
            ) from error
