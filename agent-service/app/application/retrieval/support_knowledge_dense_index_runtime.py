from __future__ import annotations

from threading import RLock

from app.application.retrieval.support_knowledge_dense_index_preparation import (
    DenseSupportKnowledgeIndexPreparationResult,
    SupportKnowledgeDenseIndexPreparationService,
)
from app.application.retrieval.dense_support_knowledge_chunk_retrieval import (
    DenseSupportKnowledgeChunkRetriever,
)
from app.application.retrieval.support_knowledge_chunk_retrieval import (
    SupportKnowledgeChunkSearchHit,
)
from app.domain.dense_support_knowledge_index import (
    DenseSupportKnowledgeIndexSnapshot,
    DenseSupportKnowledgeIndexStore,
    SupportKnowledgeTextEmbedder,
)
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus


class DenseSupportKnowledgeIndexNotPreparedError(RuntimeError):
    """The process has no verified dense snapshot for the current corpus yet."""


class SupportKnowledgeDenseIndexRuntime:
    """Owns one process-local offline dense index and refreshes it outside searches."""

    def __init__(
        self,
        corpus: CurrentSupportKnowledgeCorpus,
        embedder: SupportKnowledgeTextEmbedder,
        store: DenseSupportKnowledgeIndexStore,
    ) -> None:
        self._corpus = corpus
        self._embedder = embedder
        self._store = store
        self._lock = RLock()
        self._snapshot: DenseSupportKnowledgeIndexSnapshot | None = None

    def prepare(self) -> DenseSupportKnowledgeIndexPreparationResult:
        """Build or reuse a compatible snapshot; never invoke this from search()."""
        with self._lock:
            result = SupportKnowledgeDenseIndexPreparationService(
                self._corpus,
                self._embedder,
                self._store,
            ).prepare()
            self._snapshot = result.snapshot
            return result

    def refresh(self) -> DenseSupportKnowledgeIndexPreparationResult:
        """Refresh after an administrator has changed the current corpus."""
        return self.prepare()

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        """Embed only the query and search the already prepared document vectors."""
        # Capture one immutable snapshot.  The retriever verifies it against the
        # current corpus before ranking, so an old snapshot cannot be used silently.
        return DenseSupportKnowledgeChunkRetriever(
            self._corpus,
            self.snapshot,
            self._embedder,
            vector_store=self._store if callable(getattr(self._store, "search", None)) else None,
        ).search(query, top_k=top_k)

    @property
    def snapshot(self) -> DenseSupportKnowledgeIndexSnapshot:
        with self._lock:
            if self._snapshot is None:
                raise DenseSupportKnowledgeIndexNotPreparedError(
                    "dense support knowledge index has not been prepared"
                )
            return self._snapshot

    def close(self) -> None:
        close = getattr(self._embedder, "close", None)
        if callable(close):
            close()
