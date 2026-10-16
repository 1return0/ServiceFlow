from __future__ import annotations

from dataclasses import dataclass
from unittest import TestCase

from app.application.retrieval.dense_support_knowledge_chunk_retrieval import (
    DenseSupportKnowledgeChunkRetriever,
    DenseSupportKnowledgeIndexUnavailableError,
)
from app.application.retrieval.support_knowledge_dense_index_preparation import (
    SupportKnowledgeDenseIndexPreparationService,
)
from app.domain.dense_support_knowledge_index import (
    DenseEmbeddingIdentity,
    DenseSupportKnowledgeIndexSnapshot,
)
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


class DenseSupportKnowledgeChunkRetrieverTest(TestCase):
    def test_returns_dense_top_k_without_reembedding_documents(self) -> None:
        corpus = _corpus()
        embedder = _StubEmbedder()
        snapshot = _prepare_snapshot(corpus, embedder)

        hits = DenseSupportKnowledgeChunkRetriever(corpus, snapshot, embedder).search(
            "我连不上校园网",
            top_k=1,
        )

        self.assertEqual(("chunk-network",), tuple(hit.chunk.chunk_id for hit in hits))
        self.assertEqual(1, embedder.document_calls)
        self.assertEqual(1, embedder.query_calls)

    def test_rejects_a_stale_index_instead_of_reembedding_documents_online(self) -> None:
        corpus = _corpus()
        embedder = _StubEmbedder()
        snapshot = _prepare_snapshot(corpus, embedder)
        corpus.upsert_with_chunks(
            _article("classroom"),
            (_chunk("chunk-classroom", "教室设备报修", article_id="classroom"),),
        )

        with self.assertRaises(DenseSupportKnowledgeIndexUnavailableError):
            DenseSupportKnowledgeChunkRetriever(corpus, snapshot, embedder).search("借书")

        self.assertEqual(1, embedder.document_calls)


@dataclass
class _StubEmbedder:
    document_calls: int = 0
    query_calls: int = 0

    @property
    def embedding_identity(self) -> DenseEmbeddingIdentity:
        return DenseEmbeddingIdentity("test", "stub", "revision-a", 2)

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.document_calls += 1
        return tuple(
            (1.0, 0.0) if "网络" in text else (0.0, 1.0) for text in texts
        )

    def embed_query(self, text: str) -> tuple[float, ...]:
        self.query_calls += 1
        return (1.0, 0.0)


def _prepare_snapshot(
    corpus: InMemoryCurrentSupportKnowledgeCorpus,
    embedder: _StubEmbedder,
) -> DenseSupportKnowledgeIndexSnapshot:
    store = _InMemoryIndexStore()
    return SupportKnowledgeDenseIndexPreparationService(corpus, embedder, store).prepare().snapshot


class _InMemoryIndexStore:
    def __init__(self) -> None:
        self.snapshot: DenseSupportKnowledgeIndexSnapshot | None = None

    def load(self) -> DenseSupportKnowledgeIndexSnapshot | None:
        return self.snapshot

    def save(self, snapshot: DenseSupportKnowledgeIndexSnapshot) -> None:
        self.snapshot = snapshot


def _corpus() -> InMemoryCurrentSupportKnowledgeCorpus:
    corpus = InMemoryCurrentSupportKnowledgeCorpus(())
    corpus.upsert_with_chunks(_article("network"), (_chunk("chunk-network", "校园网络连接"),))
    corpus.upsert_with_chunks(_article("library"), (_chunk("chunk-library", "图书馆借阅"),))
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


def _chunk(
    chunk_id: str,
    text: str,
    *,
    article_id: str | None = None,
) -> SupportKnowledgeChunk:
    return SupportKnowledgeChunk(
        chunk_id=chunk_id,
        article_id=(
            article_id
            if article_id is not None
            else "network" if chunk_id == "chunk-network" else "library"
        ),
        text=text,
        fragment_ordinal=1,
        fragment_location="paragraph:1",
        fragment_char_start=0,
        fragment_char_end=len(text),
        chunker_version="test-v1",
    )
