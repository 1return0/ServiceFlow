from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


class PlannerEvaluationAggregationError(ValueError):
    """Reports cannot be safely compared as one experiment."""


@dataclass(frozen=True)
class PlannerEvaluationAggregate:
    run_count: int
    planner_identity: str
    prompt_version: str | None
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    average_decision_accuracy: float
    average_case_accuracy: float
    minimum_case_accuracy: float
    average_ticket_id_accuracy: float | None
    failure_code_counts: dict[str, int]


def aggregate_planner_evaluation_reports(
    report_paths: tuple[Path, ...],
) -> PlannerEvaluationAggregate:
    if len(report_paths) < 2:
        raise PlannerEvaluationAggregationError(
            "at least two reports are required for an aggregate"
        )

    reports = tuple(_load_report(path) for path in report_paths)
    first_report = reports[0]
    compatibility_fields = (
        "planner_identity",
        "prompt_version",
        "dataset_id",
        "dataset_version",
        "dataset_sha256",
    )
    for report in reports[1:]:
        for field_name in compatibility_fields:
            if report[field_name] != first_report[field_name]:
                raise PlannerEvaluationAggregationError(
                    f"report mismatch for {field_name}"
                )

    ticket_id_accuracies = tuple(
        report["ticket_id_accuracy"]
        for report in reports
        if report["ticket_id_accuracy"] is not None
    )
    failure_code_counts = Counter(
        failure_code
        for report in reports
        for case in report["cases"]
        if (failure_code := case.get("failure_code")) is not None
    )
    return PlannerEvaluationAggregate(
        run_count=len(reports),
        planner_identity=first_report["planner_identity"],
        prompt_version=first_report["prompt_version"],
        dataset_id=first_report["dataset_id"],
        dataset_version=first_report["dataset_version"],
        dataset_sha256=first_report["dataset_sha256"],
        average_decision_accuracy=mean(
            report["decision_accuracy"] for report in reports
        ),
        average_case_accuracy=mean(
            report["case_accuracy"] for report in reports
        ),
        minimum_case_accuracy=min(
            report["case_accuracy"] for report in reports
        ),
        average_ticket_id_accuracy=(
            mean(ticket_id_accuracies) if ticket_id_accuracies else None
        ),
        failure_code_counts=dict(sorted(failure_code_counts.items())),
    )


def _load_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PlannerEvaluationAggregationError(
            f"could not read planner evaluation report: {path.name}"
        ) from error
    if not isinstance(payload, dict):
        raise PlannerEvaluationAggregationError(
            f"planner evaluation report must be a JSON object: {path.name}"
        )

    required_fields = (
        "planner_identity",
        "prompt_version",
        "dataset_id",
        "dataset_version",
        "dataset_sha256",
        "decision_accuracy",
        "ticket_id_accuracy",
        "case_accuracy",
        "cases",
    )
    if any(field_name not in payload for field_name in required_fields):
        raise PlannerEvaluationAggregationError(
            f"planner evaluation report is missing required fields: {path.name}"
        )
    if not isinstance(payload["cases"], list):
        raise PlannerEvaluationAggregationError(
            f"planner evaluation report cases must be a list: {path.name}"
        )
    return payload
