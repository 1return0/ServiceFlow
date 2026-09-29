from __future__ import annotations

from dataclasses import dataclass
from unittest import TestCase

from app.application.support_knowledge_dense_index_runtime import (
    SupportKnowledgeDenseIndexRuntime,
)
from app.application.dense_support_knowledge_chunk_retrieval import (
    DenseSupportKnowledgeIndexUnavailableError,
)
from app.domain.dense_support_knowledge_index import (
    DenseEmbeddingIdentity,
    DenseSupportKnowledgeIndexSnapshot,
)
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


class SupportKnowledgeDenseIndexRuntimeTest(TestCase):
    def test_reuses_then_rebuilds_after_a_corpus_change(self) -> None:
        corpus = _corpus()
        embedder = _Embedder()
        runtime = SupportKnowledgeDenseIndexRuntime(corpus, embedder, _IndexStore())

        first = runtime.prepare()
        second = runtime.prepare()
        corpus.upsert_with_chunks(
            _article("library"),
            (_chunk("chunk-library", "图书馆借阅", "library"),),
        )
        refreshed = runtime.prepare()

        self.assertFalse(first.reused_existing_index)
        self.assertTrue(second.reused_existing_index)
        self.assertFalse(refreshed.reused_existing_index)
        self.assertEqual(2, embedder.document_calls)
        self.assertEqual(2, len(runtime.snapshot.vectors))

    def test_online_search_embeds_only_the_query_and_rejects_a_stale_snapshot(self) -> None:
        corpus = _corpus()
        embedder = _Embedder()
        runtime = SupportKnowledgeDenseIndexRuntime(corpus, embedder, _IndexStore())
        runtime.prepare()

        hits = runtime.search("校园网络", top_k=1)
        self.assertEqual("chunk-network", hits[0].chunk.chunk_id)
        self.assertEqual(1, embedder.document_calls)
        self.assertEqual(1, embedder.query_calls)

        corpus.upsert_with_chunks(
            _article("library"),
            (_chunk("chunk-library", "图书馆借阅", "library"),),
        )
        with self.assertRaises(DenseSupportKnowledgeIndexUnavailableError):
            runtime.search("图书馆")
        self.assertEqual(1, embedder.document_calls)
        self.assertEqual(1, embedder.query_calls)


@dataclass
class _Embedder:
    document_calls: int = 0
    query_calls: int = 0

    @property
    def embedding_identity(self) -> DenseEmbeddingIdentity:
        return DenseEmbeddingIdentity("test", "stub", "revision-a", 2)

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.document_calls += 1
        return tuple((float(index + 1), 1.0) for index, _text in enumerate(texts))

    def embed_query(self, text: str) -> tuple[float, ...]:
        self.query_calls += 1
        return (1.0, 1.0)


class _IndexStore:
    def __init__(self) -> None:
        self.snapshot: DenseSupportKnowledgeIndexSnapshot | None = None

    def load(self) -> DenseSupportKnowledgeIndexSnapshot | None:
        return self.snapshot

    def save(self, snapshot: DenseSupportKnowledgeIndexSnapshot) -> None:
        self.snapshot = snapshot


def _corpus() -> InMemoryCurrentSupportKnowledgeCorpus:
    corpus = InMemoryCurrentSupportKnowledgeCorpus(())
    corpus.upsert_with_chunks(
        _article("network"),
        (_chunk("chunk-network", "校园网络连接", "network"),),
    )
    return corpus


def _article(article_id: str) -> SupportKnowledgeArticle:
    return SupportKnowledgeArticle(
        article_id=article_id,
        category="campus_network",
        title=article_id,
        content=article_id,
        source_reference="https://it.example.edu/guide",
        source_kind="official_campus",
        source_content_sha256="a" * 64,
        source_review_status="reviewed",
        source_review_reference="review-1",
        corpus_version="v1",
    )


def _chunk(chunk_id: str, text: str, article_id: str) -> SupportKnowledgeChunk:
    return SupportKnowledgeChunk(
        chunk_id=chunk_id,
        article_id=article_id,
        text=text,
        fragment_ordinal=1,
        fragment_location="paragraph:1",
        fragment_char_start=0,
        fragment_char_end=len(text),
        chunker_version="test-v1",
    )
