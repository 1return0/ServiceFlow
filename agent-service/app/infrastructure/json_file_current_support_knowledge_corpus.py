from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.in_memory_support_knowledge_corpus import (
    SupportKnowledgeCorpusConflictError,
)


class SupportKnowledgeCorpusPersistenceError(RuntimeError):
    """The durable current-corpus state cannot be safely read or written."""


class _StoredArticle(BaseModel):
    article_id: str
    category: Literal[
        "account", "campus_network", "teaching_system", "classroom_equipment", "service_process"
    ]
    title: str
    content: str
    source_reference: str
    source_kind: Literal["official_campus", "demonstration"]
    source_content_sha256: str
    source_review_status: Literal["reviewed", "demonstration"]
    source_review_reference: str
    corpus_version: str


class _StoredCorpus(BaseModel):
    schema_version: Literal[1]
    imported_articles: list[_StoredArticle]
    imported_chunks: list[dict[str, object]] = Field(default_factory=list)


class JsonFileCurrentSupportKnowledgeCorpus:
    """Current corpus that restores imported articles after a process restart."""

    def __init__(
        self,
        seed_articles: tuple[SupportKnowledgeArticle, ...],
        state_path: Path,
    ) -> None:
        self._lock = RLock()
        self._state_path = state_path
        self._articles_by_id = {article.article_id: article for article in seed_articles}
        if len(self._articles_by_id) != len(seed_articles):
            raise ValueError("seed articles must have unique article IDs")
        self._imported_article_ids: set[str] = set()
        self._revision = 0
        self._chunks_by_id: dict[str, SupportKnowledgeChunk] = {
            chunk.chunk_id: chunk
            for chunk in (self._seed_chunk(article) for article in seed_articles)
        }
        self._load_imported_articles()

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def list_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        return self.snapshot()[1]

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

            candidate_articles = dict(self._articles_by_id)
            candidate_articles[article.article_id] = article
            candidate_imported_ids = self._imported_article_ids | {article.article_id}
            candidate_chunks = dict(self._chunks_by_id)
            candidate_chunks.update({chunk.chunk_id: chunk for chunk in chunks})
            self._write_state(
                candidate_articles, candidate_imported_ids, candidate_chunks
            )
            self._articles_by_id = candidate_articles
            self._imported_article_ids = candidate_imported_ids
            self._chunks_by_id = candidate_chunks
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
                )
            )

    def _load_imported_articles(self) -> None:
        if not self._state_path.exists():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            state = _StoredCorpus.model_validate(raw)
            for payload in state.imported_articles:
                article = self._to_article(payload)
                existing = self._articles_by_id.get(article.article_id)
                if existing is not None and (
                    existing.source_content_sha256 != article.source_content_sha256
                ):
                    raise ValueError("persisted article conflicts with seed corpus")
                self._articles_by_id[article.article_id] = article
                self._imported_article_ids.add(article.article_id)
            for row in state.imported_chunks:
                chunk = SupportKnowledgeChunk(**row)  # type: ignore[arg-type]
                if chunk.article_id not in self._articles_by_id:
                    raise ValueError("persisted chunk has no matching article")
                self._chunks_by_id[chunk.chunk_id] = chunk
        except (OSError, TypeError, ValueError, ValidationError, json.JSONDecodeError) as error:
            raise SupportKnowledgeCorpusPersistenceError(
                "current support knowledge corpus state could not be loaded"
            ) from error

    def _write_state(
        self,
        articles_by_id: dict[str, SupportKnowledgeArticle],
        imported_article_ids: set[str],
        chunks_by_id: dict[str, SupportKnowledgeChunk],
    ) -> None:
        payload = {
            "schema_version": 1,
            "imported_articles": [
                asdict(articles_by_id[article_id])
                for article_id in sorted(imported_article_ids)
            ],
            "imported_chunks": [
                asdict(chunks_by_id[chunk_id]) for chunk_id in sorted(chunks_by_id)
            ],
        }
        temporary_path = self._state_path.with_suffix(
            f"{self._state_path.suffix}.tmp"
        )
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temporary_path.replace(self._state_path)
        except OSError as error:
            raise SupportKnowledgeCorpusPersistenceError(
                "current support knowledge corpus state could not be saved"
            ) from error

    @staticmethod
    def _to_article(payload: _StoredArticle) -> SupportKnowledgeArticle:
        expected_hash = hashlib.sha256(
            f"{payload.title}\n{payload.content}".encode("utf-8")
        ).hexdigest()
        if expected_hash != payload.source_content_sha256:
            raise ValueError("persisted article content hash mismatch")
        return SupportKnowledgeArticle(**payload.model_dump())

    def _ordered_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        return tuple(
            self._articles_by_id[article_id]
            for article_id in sorted(self._articles_by_id)
        )

    @staticmethod
    def _seed_chunk(article: SupportKnowledgeArticle) -> SupportKnowledgeChunk:
        identity = hashlib.sha256(
            f"seed-article-v1\n{article.article_id}\n{article.content}".encode("utf-8")
        ).hexdigest()
        return SupportKnowledgeChunk(
            chunk_id=f"chunk_{identity}",
            article_id=article.article_id,
            text=article.content,
            fragment_ordinal=1,
            fragment_location="seed:article",
            fragment_char_start=0,
            fragment_char_end=len(article.content),
            chunker_version="seed-article-v1",
        )
