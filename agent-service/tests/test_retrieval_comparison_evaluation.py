from __future__ import annotations

import json
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.evaluation.retrieval_comparison_evaluation import (
    RetrievalComparisonEvaluationError,
    run_retrieval_comparison_evaluation,
    write_retrieval_comparison_report,
)
from app.application.retrieval.support_knowledge_chunk_retrieval import SupportKnowledgeChunkSearchHit
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


class RetrievalComparisonEvaluationTest(TestCase):
    def test_compares_exactly_four_variants_against_one_frozen_dataset(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset_path = root / "golden.json"
            dataset_path.write_text(json.dumps(_dataset()), encoding="utf-8")
            corpus = _corpus()
            chunk = corpus.retrieval_snapshot()[2][0]
            retrievers = OrderedDict(
                (variant, _StaticRetriever(chunk))
                for variant in ("bm25", "dense", "hybrid", "hybrid_rerank")
            )

            report = run_retrieval_comparison_evaluation(
                corpus=corpus,
                retrievers=retrievers,
                dataset_path=dataset_path,
                top_k=1,
                evaluated_at=datetime(2026, 9, 26, tzinfo=UTC),
            )

            self.assertEqual(4, len(report.variants))
            self.assertEqual("bm25", report.variants[0].variant)
            self.assertEqual(1.0, report.variants[3].mean_ndcg_at_k)
            report_path = root / "comparison.json"
            write_retrieval_comparison_report(report, report_path)
            with self.assertRaises(FileExistsError):
                write_retrieval_comparison_report(report, report_path)

    def test_rejects_golden_chunk_ids_not_in_the_evaluated_corpus(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset_path = root / "golden.json"
            dataset_path.write_text(json.dumps(_dataset(chunk_id="missing")), encoding="utf-8")
            chunk = _corpus().retrieval_snapshot()[2][0]
            retrievers = OrderedDict(
                (variant, _StaticRetriever(chunk))
                for variant in ("bm25", "dense", "hybrid", "hybrid_rerank")
            )

            with self.assertRaises(RetrievalComparisonEvaluationError):
                run_retrieval_comparison_evaluation(
                    corpus=_corpus(),
                    retrievers=retrievers,
                    dataset_path=dataset_path,
                    top_k=1,
                )


class _StaticRetriever:
    def __init__(self, chunk: SupportKnowledgeChunk) -> None:
        self._chunk = chunk

    def search(self, query: str, *, top_k: int = 3):
        return (SupportKnowledgeChunkSearchHit(self._chunk, 1.0),)


def _corpus() -> InMemoryCurrentSupportKnowledgeCorpus:
    corpus = InMemoryCurrentSupportKnowledgeCorpus(())
    corpus.upsert_with_chunks(
        SupportKnowledgeArticle(
            article_id="network",
            category="campus_network",
            title="Network",
            content="Network guide",
            source_reference="https://it.example.edu/network",
            source_kind="official_campus",
            source_content_sha256="a" * 64,
            source_review_status="reviewed",
            source_review_reference="review-1",
            corpus_version="v1",
        ),
        (
            SupportKnowledgeChunk(
                chunk_id="chunk-network",
                article_id="network",
                text="校园网络认证",
                fragment_ordinal=1,
                fragment_location="paragraph:1",
                fragment_char_start=0,
                fragment_char_end=6,
                chunker_version="test-v1",
            ),
        ),
    )
    return corpus


def _dataset(*, chunk_id: str = "chunk-network") -> dict[str, object]:
    return {
        "dataset_id": "retrieval-comparison-v1",
        "dataset_version": 1,
        "cases": [{
            "case_id": "network",
            "query": "校园网络",
            "judgments": [{"chunk_id": chunk_id, "relevance_grade": 3}],
        }],
    }
