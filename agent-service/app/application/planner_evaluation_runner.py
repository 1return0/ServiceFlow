from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.application.planner_evaluation import PlannerEvaluator
from app.application.planner_evaluation_dataset import (
    PlannerEvaluationDataset,
    load_planner_evaluation_dataset,
)
from app.domain.ticket_lookup_plan import TicketLookupPlanner


@dataclass(frozen=True)
class PlannerEvaluationRunReport:
    evaluated_at: str
    planner_identity: str
    prompt_version: str | None
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    total_cases: int
    passed_cases: int
    decision_accuracy: float
    ticket_id_evaluated_cases: int
    ticket_id_accuracy: float | None
    case_accuracy: float
    cases: tuple[dict[str, Any], ...]


def run_planner_evaluation(
    *,
    planner: TicketLookupPlanner,
    dataset_path: Path,
    evaluated_at: datetime | None = None,
) -> PlannerEvaluationRunReport:
    dataset = load_planner_evaluation_dataset(dataset_path)
    summary = PlannerEvaluator().evaluate(planner, dataset.cases)
    return PlannerEvaluationRunReport(
        evaluated_at=(evaluated_at or datetime.now(UTC)).isoformat(),
        planner_identity=_planner_identity(planner),
        prompt_version=_planner_prompt_version(planner),
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset.dataset_sha256,
        total_cases=summary.total_cases,
        passed_cases=summary.passed_cases,
        decision_accuracy=summary.decision_accuracy,
        ticket_id_evaluated_cases=summary.ticket_id_evaluated_cases,
        ticket_id_accuracy=summary.ticket_id_accuracy,
        case_accuracy=summary.case_accuracy,
        cases=tuple(
            {
                "case_id": result.case_id,
                "passed": result.passed,
                "expected_decision": result.expected_decision,
                "expected_ticket_id": str(result.expected_ticket_id)
                if result.expected_ticket_id
                else None,
                "actual_plan": (
                    result.actual_plan.model_dump(mode="json")
                    if result.actual_plan is not None
                    else None
                ),
                "failure_code": result.failure_code,
            }
            for result in summary.results
        ),
    )


def write_planner_evaluation_report(
    report: PlannerEvaluationRunReport,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as report_file:
        json.dump(
            asdict(report),
            report_file,
            ensure_ascii=False,
            indent=2,
        )
        report_file.write("\n")


def _planner_identity(planner: TicketLookupPlanner) -> str:
    identity = getattr(planner, "identity", None)
    if isinstance(identity, str) and identity.strip():
        return identity
    planner_type = type(planner)
    return f"{planner_type.__module__}.{planner_type.__qualname__}"


def _planner_prompt_version(planner: TicketLookupPlanner) -> str | None:
    prompt_version = getattr(planner, "prompt_version", None)
    if isinstance(prompt_version, str) and prompt_version.strip():
        return prompt_version
    return None
