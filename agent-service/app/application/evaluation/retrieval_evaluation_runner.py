from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.application.evaluation.retrieval_evaluation import (
    RetrievalEvaluator,
    SupportKnowledgeChunkSearcher,
)
from app.application.evaluation.retrieval_evaluation_dataset import (
    load_retrieval_evaluation_dataset,
)


@dataclass(frozen=True)
class RetrievalEvaluationRunReport:
    evaluated_at: str
    retriever_identity: str
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    top_k: int
    recall_at_k: float
    mean_reciprocal_rank: float
    mean_ndcg_at_k: float
    cases: tuple[dict[str, object], ...]


def run_retrieval_evaluation(
    *,
    retriever: SupportKnowledgeChunkSearcher,
    dataset_path: Path,
    top_k: int,
) -> RetrievalEvaluationRunReport:
    dataset = load_retrieval_evaluation_dataset(dataset_path)
    summary = RetrievalEvaluator().evaluate(retriever, dataset.cases, top_k=top_k)
    return RetrievalEvaluationRunReport(
        evaluated_at=datetime.now(UTC).isoformat(),
        retriever_identity=f"{type(retriever).__module__}.{type(retriever).__qualname__}",
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset.dataset_sha256,
        top_k=top_k,
        recall_at_k=summary.recall_at_k,
        mean_reciprocal_rank=summary.mean_reciprocal_rank,
        mean_ndcg_at_k=summary.mean_ndcg_at_k,
        cases=tuple(asdict(case) for case in summary.cases),
    )


def write_retrieval_evaluation_report(
    report: RetrievalEvaluationRunReport,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as report_file:
        json.dump(asdict(report), report_file, ensure_ascii=False, indent=2)
        report_file.write("\n")
