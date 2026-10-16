from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.application.evaluation.planner_evaluation import PlannerEvaluationCase


class PlannerEvaluationDatasetError(ValueError):
    """The golden planning dataset could not be loaded as a valid contract."""


class _PlannerEvaluationCaseFile(BaseModel):
    case_id: str
    user_query: str
    expected_decision: Literal["lookup_ticket", "refuse"]
    expected_ticket_id: UUID | None = None


class _PlannerEvaluationDatasetFile(BaseModel):
    dataset_id: str
    dataset_version: int
    cases: tuple[_PlannerEvaluationCaseFile, ...]


@dataclass(frozen=True)
class PlannerEvaluationDataset:
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    cases: tuple[PlannerEvaluationCase, ...]


def load_planner_evaluation_dataset(path: Path) -> PlannerEvaluationDataset:
    try:
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes)
        parsed = _PlannerEvaluationDatasetFile.model_validate(payload)
        cases = tuple(
            PlannerEvaluationCase(
                case_id=case.case_id,
                user_query=case.user_query,
                expected_decision=case.expected_decision,
                expected_ticket_id=case.expected_ticket_id,
            )
            for case in parsed.cases
        )
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as error:
        raise PlannerEvaluationDatasetError(
            "planner evaluation dataset is invalid"
        ) from error

    if not cases:
        raise PlannerEvaluationDatasetError(
            "planner evaluation dataset must contain at least one case"
        )
    return PlannerEvaluationDataset(
        dataset_id=parsed.dataset_id,
        dataset_version=parsed.dataset_version,
        dataset_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        cases=cases,
    )
