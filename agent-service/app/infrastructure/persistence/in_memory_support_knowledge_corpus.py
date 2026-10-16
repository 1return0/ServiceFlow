from __future__ import annotations

from threading import RLock

from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class SupportKnowledgeCorpusConflictError(ValueError):
    """An article identity is being reused for different source content."""


class InMemoryCurrentSupportKnowledgeCorpus:
    """Process-local current corpus with explicit idempotency semantics."""

    def __init__(self, seed_articles: tuple[SupportKnowledgeArticle, ...]) -> None:
        self._lock = RLock()
        self._articles_by_id = {article.article_id: article for article in seed_articles}
        if len(self._articles_by_id) != len(seed_articles):
            raise ValueError("seed articles must have unique article IDs")
        self._revision = 0
        self._chunks_by_id: dict[str, SupportKnowledgeChunk] = {}

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def list_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        with self._lock:
            return self._ordered_articles()

    def snapshot(self) -> tuple[int, tuple[SupportKnowledgeArticle, ...]]:
        with self._lock:
            return self._revision, self._ordered_articles()

    def upsert(self, article: SupportKnowledgeArticle) -> bool:
        return self.upsert_with_chunks(article, ())

    def upsert_with_chunks(
        self,
        article: SupportKnowledgeArticle,
        chunks: tuple[SupportKnowledgeChunk, ...],
    ) -> bool:
        with self._lock:
            existing = self._articles_by_id.get(article.article_id)
            if existing is not None and existing.source_content_sha256 != article.source_content_sha256:
                raise SupportKnowledgeCorpusConflictError(
                    "article_id already belongs to different source content"
                )
            if any(chunk.article_id != article.article_id for chunk in chunks):
                raise SupportKnowledgeCorpusConflictError(
                    "all chunks must belong to the supplied article"
                )
            changed = existing is None or any(
                chunk.chunk_id not in self._chunks_by_id for chunk in chunks
            )
            if not changed:
                return False
            self._articles_by_id[article.article_id] = article
            self._chunks_by_id.update({chunk.chunk_id: chunk for chunk in chunks})
            self._revision += 1
            return True

    def chunk_snapshot(self) -> tuple[int, tuple[SupportKnowledgeChunk, ...]]:
        with self._lock:
            return self._revision, tuple(
                self._chunks_by_id[chunk_id] for chunk_id in sorted(self._chunks_by_id)
            )

    def retrieval_snapshot(self):
        with self._lock:
            return (
                self._revision,
                self._ordered_articles(),
                tuple(
                    self._chunks_by_id[chunk_id]
                    for chunk_id in sorted(self._chunks_by_id)
                ),
            )

    def _ordered_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        return tuple(
            self._articles_by_id[article_id]
            for article_id in sorted(self._articles_by_id)
        )
