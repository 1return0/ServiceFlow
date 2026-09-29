from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.retrieval_evaluation_dataset import (
    load_retrieval_evaluation_dataset,
)
from app.application.retrieval_evaluation_runner import (
    run_retrieval_evaluation,
    write_retrieval_evaluation_report,
)
from app.application.support_knowledge_chunk_retrieval import SupportKnowledgeChunkSearchHit
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class RetrievalEvaluationDatasetAndRunnerTest(TestCase):
    def test_hashes_the_frozen_dataset_and_never_overwrites_a_report(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset_path = root / "golden.json"
            dataset_path.write_text(json.dumps(_dataset()), encoding="utf-8")
            dataset = load_retrieval_evaluation_dataset(dataset_path)
            report = run_retrieval_evaluation(
                retriever=_StaticRetriever(), dataset_path=dataset_path, top_k=1
            )
            report_path = root / "report.json"
            write_retrieval_evaluation_report(report, report_path)

            self.assertEqual(dataset.dataset_sha256, report.dataset_sha256)
            with self.assertRaises(FileExistsError):
                write_retrieval_evaluation_report(report, report_path)


class _StaticRetriever:
    def search(self, query: str, *, top_k: int = 3):
        return (
            SupportKnowledgeChunkSearchHit(
                SupportKnowledgeChunk(
                    "chunk-network", "network", "校园网", 1, "p:1", 0, 3, "v1"
                ),
                1.0,
            ),
        )


def _dataset() -> dict[str, object]:
    return {
        "dataset_id": "support-knowledge-retrieval-v1",
        "dataset_version": 1,
        "cases": [
            {
                "case_id": "network",
                "query": "校园网",
                "judgments": [
                    {"chunk_id": "chunk-network", "relevance_grade": 3}
                ],
            }
        ],
    }
