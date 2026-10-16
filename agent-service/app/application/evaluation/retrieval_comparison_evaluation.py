from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

from app.application.evaluation.retrieval_evaluation import (
    RetrievalEvaluator,
    RetrievalEvaluationSummary,
    SupportKnowledgeChunkSearcher,
)
from app.application.evaluation.retrieval_evaluation_dataset import (
    RetrievalEvaluationDataset,
    load_retrieval_evaluation_dataset,
)
from app.application.retrieval.support_knowledge_dense_index_preparation import (
    calculate_dense_corpus_fingerprint,
)
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus


_REQUIRED_VARIANTS = ("bm25", "dense", "hybrid", "hybrid_rerank")


class RetrievalComparisonEvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class RetrievalVariantReport:
    variant: str
    retriever_identity: str
    recall_at_k: float
    mean_reciprocal_rank: float
    mean_ndcg_at_k: float
    cases: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class RetrievalComparisonReport:
    evaluated_at: str
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    corpus_revision: int
    corpus_fingerprint: str
    top_k: int
    variants: tuple[RetrievalVariantReport, ...]


def run_retrieval_comparison_evaluation(
    *,
    corpus: CurrentSupportKnowledgeCorpus,
    retrievers: Mapping[str, SupportKnowledgeChunkSearcher],
    dataset_path: Path,
    top_k: int,
    evaluated_at: datetime | None = None,
) -> RetrievalComparisonReport:
    if tuple(retrievers) != _REQUIRED_VARIANTS:
        raise RetrievalComparisonEvaluationError(
            "retrievers must contain bm25, dense, hybrid, hybrid_rerank in that order"
        )
    dataset = load_retrieval_evaluation_dataset(dataset_path)
    revision, _articles, chunks = corpus.retrieval_snapshot()
    _validate_golden_chunks(dataset, {chunk.chunk_id for chunk in chunks})
    evaluator = RetrievalEvaluator()
    variant_reports = tuple(
        _to_variant_report(
            variant,
            retriever,
            evaluator.evaluate(retriever, dataset.cases, top_k=top_k),
        )
        for variant, retriever in retrievers.items()
    )
    return RetrievalComparisonReport(
        evaluated_at=(evaluated_at or datetime.now(UTC)).isoformat(),
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset.dataset_sha256,
        corpus_revision=revision,
        corpus_fingerprint=calculate_dense_corpus_fingerprint(chunks),
        top_k=top_k,
        variants=variant_reports,
    )


def write_retrieval_comparison_report(
    report: RetrievalComparisonReport,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as report_file:
        json.dump(asdict(report), report_file, ensure_ascii=False, indent=2)
        report_file.write("\n")


def _validate_golden_chunks(
    dataset: RetrievalEvaluationDataset,
    available_chunk_ids: set[str],
) -> None:
    unknown = sorted(
        judgment.chunk_id
        for case in dataset.cases
        for judgment in case.judgments
        if judgment.chunk_id not in available_chunk_ids
    )
    if unknown:
        raise RetrievalComparisonEvaluationError(
            "golden retrieval dataset references chunks outside the current corpus: "
            + ", ".join(unknown)
        )


def _to_variant_report(
    variant: str,
    retriever: SupportKnowledgeChunkSearcher,
    summary: RetrievalEvaluationSummary,
) -> RetrievalVariantReport:
    return RetrievalVariantReport(
        variant=variant,
        retriever_identity=(
            f"{type(retriever).__module__}.{type(retriever).__qualname__}"
        ),
        recall_at_k=summary.recall_at_k,
        mean_reciprocal_rank=summary.mean_reciprocal_rank,
        mean_ndcg_at_k=summary.mean_ndcg_at_k,
        cases=tuple(asdict(case) for case in summary.cases),
    )
