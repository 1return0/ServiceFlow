from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.application.multi_agent_evaluation import (
    MultiAgentEvaluationCase,
    TriageDecision,
)


class MultiAgentEvaluationDatasetError(ValueError):
    """The immutable multi-agent evaluation input is invalid."""


class _CaseFile(BaseModel):
    case_id: str
    user_query: str
    expected_decision: TriageDecision | None = None
    expected_required_nodes: tuple[str, ...]
    authorization: str | None = None
    expected_failure_code: str | None = None


class _DatasetFile(BaseModel):
    dataset_id: str
    dataset_version: int
    cases: tuple[_CaseFile, ...]


@dataclass(frozen=True)
class MultiAgentEvaluationDataset:
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    cases: tuple[MultiAgentEvaluationCase, ...]


def load_multi_agent_evaluation_dataset(path: Path) -> MultiAgentEvaluationDataset:
    try:
        raw_bytes = path.read_bytes()
        parsed = _DatasetFile.model_validate(json.loads(raw_bytes))
        cases = tuple(
            MultiAgentEvaluationCase(
                case_id=case.case_id,
                user_query=case.user_query,
                expected_decision=case.expected_decision,
                expected_required_nodes=case.expected_required_nodes,
                authorization=case.authorization,
                expected_failure_code=case.expected_failure_code,
            )
            for case in parsed.cases
        )
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as error:
        raise MultiAgentEvaluationDatasetError(
            "multi-agent evaluation dataset is invalid"
        ) from error
    if not cases:
        raise MultiAgentEvaluationDatasetError(
            "multi-agent evaluation dataset must contain at least one case"
        )
    if len({case.case_id for case in cases}) != len(cases):
        raise MultiAgentEvaluationDatasetError(
            "multi-agent evaluation case IDs must be unique"
        )
    return MultiAgentEvaluationDataset(
        dataset_id=parsed.dataset_id,
        dataset_version=parsed.dataset_version,
        dataset_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        cases=cases,
    )
