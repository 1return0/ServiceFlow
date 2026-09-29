from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.support_knowledge_dense_index_preparation import (
    DenseSupportKnowledgeIndexBuildError,
    SupportKnowledgeDenseIndexPreparationService,
)
from app.domain.dense_support_knowledge_index import DenseEmbeddingIdentity
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)
from app.infrastructure.json_file_dense_support_knowledge_index_store import (
    JsonFileDenseSupportKnowledgeIndexStore,
)


class SupportKnowledgeDenseIndexPreparationServiceTest(TestCase):
    def test_persists_vectors_once_and_reuses_an_exact_matching_index(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        corpus.upsert_with_chunks(_article("network"), (_chunk("chunk-1", "网络连接指南"),))
        embedder = _StubEmbedder()
        with TemporaryDirectory() as directory:
            store = JsonFileDenseSupportKnowledgeIndexStore(
                Path(directory) / "dense-index.json"
            )
            service = SupportKnowledgeDenseIndexPreparationService(corpus, embedder, store)

            first = service.prepare()
            second = service.prepare()

        self.assertFalse(first.reused_existing_index)
        self.assertTrue(second.reused_existing_index)
        self.assertEqual(1, embedder.call_count)
        self.assertEqual("chunk-1", first.snapshot.vectors[0].chunk_id)

    def test_rebuilds_when_the_current_corpus_revision_and_fingerprint_change(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        corpus.upsert_with_chunks(_article("network"), (_chunk("chunk-1", "网络连接指南"),))
        embedder = _StubEmbedder()
        with TemporaryDirectory() as directory:
            service = SupportKnowledgeDenseIndexPreparationService(
                corpus,
                embedder,
                JsonFileDenseSupportKnowledgeIndexStore(Path(directory) / "index.json"),
            )
            first = service.prepare()
            corpus.upsert_with_chunks(_article("library"), (_chunk("chunk-2", "图书馆借阅服务"),))
            second = service.prepare()

        self.assertNotEqual(first.snapshot.corpus_fingerprint, second.snapshot.corpus_fingerprint)
        self.assertEqual(2, embedder.call_count)
        self.assertEqual(2, len(second.snapshot.vectors))

    def test_rejects_a_vector_result_with_the_wrong_dimension(self) -> None:
        corpus = InMemoryCurrentSupportKnowledgeCorpus(())
        corpus.upsert_with_chunks(_article("network"), (_chunk("chunk-1", "网络连接指南"),))
        with TemporaryDirectory() as directory:
            service = SupportKnowledgeDenseIndexPreparationService(
                corpus,
                _StubEmbedder(vectors=((0.1, 0.2),)),
                JsonFileDenseSupportKnowledgeIndexStore(Path(directory) / "index.json"),
            )
            with self.assertRaises(DenseSupportKnowledgeIndexBuildError):
                service.prepare()


@dataclass
class _StubEmbedder:
    vectors: tuple[tuple[float, ...], ...] = ((0.2, 0.4, 0.6),)
    call_count: int = field(default=0, init=False)

    @property
    def embedding_identity(self) -> DenseEmbeddingIdentity:
        return DenseEmbeddingIdentity("test", "stub", "revision-a", 3)

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.call_count += 1
        return tuple(self.vectors[index % len(self.vectors)] for index in range(len(texts)))


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
        article_id="network" if chunk_id == "chunk-1" else "library",
        text=text,
        fragment_ordinal=1,
        fragment_location="paragraph:1",
        fragment_char_start=0,
        fragment_char_end=len(text),
        chunker_version="test-v1",
    )
