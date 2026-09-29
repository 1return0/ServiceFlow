from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.application.retrieval_evaluation import (
    RetrievalEvaluationCase,
    RetrievalRelevanceJudgment,
)


class RetrievalEvaluationDatasetError(ValueError):
    pass


class _JudgmentFile(BaseModel):
    chunk_id: str
    relevance_grade: int = Field(ge=1)


class _CaseFile(BaseModel):
    case_id: str
    query: str
    judgments: tuple[_JudgmentFile, ...]


class _DatasetFile(BaseModel):
    dataset_id: str
    dataset_version: int = Field(ge=1)
    cases: tuple[_CaseFile, ...]


@dataclass(frozen=True)
class RetrievalEvaluationDataset:
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    cases: tuple[RetrievalEvaluationCase, ...]


def load_retrieval_evaluation_dataset(path: Path) -> RetrievalEvaluationDataset:
    try:
        raw_bytes = path.read_bytes()
        stored = _DatasetFile.model_validate(json.loads(raw_bytes))
        cases = tuple(
            RetrievalEvaluationCase(
                case_id=case.case_id,
                query=case.query,
                judgments=tuple(
                    RetrievalRelevanceJudgment(
                        chunk_id=judgment.chunk_id,
                        relevance_grade=judgment.relevance_grade,
                    )
                    for judgment in case.judgments
                ),
            )
            for case in stored.cases
        )
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as error:
        raise RetrievalEvaluationDatasetError(
            "retrieval evaluation dataset is invalid"
        ) from error
    if not cases:
        raise RetrievalEvaluationDatasetError(
            "retrieval evaluation dataset must contain at least one case"
        )
    return RetrievalEvaluationDataset(
        dataset_id=stored.dataset_id,
        dataset_version=stored.dataset_version,
        dataset_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        cases=cases,
    )
