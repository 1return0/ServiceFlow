from __future__ import annotations

from dataclasses import dataclass
from unittest import TestCase

from app.application.retrieval.dense_support_knowledge_chunk_retrieval import (
    DenseSupportKnowledgeChunkRetriever,
)
from app.application.retrieval.hybrid_support_knowledge_chunk_retriever import (
    HybridSupportKnowledgeChunkRetriever,
)
from app.application.retrieval.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever,
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


class HybridSupportKnowledgeChunkRetrieverTest(TestCase):
    def test_passes_bm25_and_dense_results_to_rrf_and_preserves_chunks(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        chunks = (
            _chunk("chunk-network", "校园网络认证"),
            _chunk("chunk-library", "图书馆借阅"),
        )
        corpus.upsert_with_chunks(_article("network"), (chunks[0],))
        corpus.upsert_with_chunks(_article("library"), (chunks[1],))
        embedder = _StubEmbedder()
        snapshot = _prepare_snapshot(corpus, embedder)
        retriever = HybridSupportKnowledgeChunkRetriever(
            LexicalSupportKnowledgeChunkRetriever(chunks),
            DenseSupportKnowledgeChunkRetriever(corpus, snapshot, embedder),
            candidate_k=2,
            rank_constant=0,
        )

        hits = retriever.search("校园网络连不上", top_k=1)

        self.assertEqual("chunk-network", hits[0].chunk.chunk_id)
        self.assertEqual("paragraph:1", hits[0].chunk.fragment_location)
        self.assertEqual(1, embedder.document_calls)
        self.assertEqual(1, embedder.query_calls)


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


class _InMemoryIndexStore:
    snapshot: DenseSupportKnowledgeIndexSnapshot | None = None

    def load(self) -> DenseSupportKnowledgeIndexSnapshot | None:
        return self.snapshot

    def save(self, snapshot: DenseSupportKnowledgeIndexSnapshot) -> None:
        self.snapshot = snapshot


def _prepare_snapshot(
    corpus: InMemoryCurrentSupportKnowledgeCorpus,
    embedder: _StubEmbedder,
) -> DenseSupportKnowledgeIndexSnapshot:
    return SupportKnowledgeDenseIndexPreparationService(
        corpus,
        embedder,
        _InMemoryIndexStore(),
    ).prepare().snapshot


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


def _chunk(chunk_id: str, text: str) -> SupportKnowledgeChunk:
    return SupportKnowledgeChunk(
        chunk_id=chunk_id,
        article_id="network" if chunk_id == "chunk-network" else "library",
        text=text,
        fragment_ordinal=1,
        fragment_location="paragraph:1",
        fragment_char_start=0,
        fragment_char_end=len(text),
        chunker_version="test-v1",
    )
