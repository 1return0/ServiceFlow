from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.evaluation.planner_evaluation_aggregation import (
    PlannerEvaluationAggregationError,
    aggregate_planner_evaluation_reports,
)


class PlannerEvaluationAggregationTest(TestCase):
    def test_aggregates_comparable_reports_and_counts_failures(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first_path = directory / "first.json"
            second_path = directory / "second.json"
            _write_report(
                first_path,
                case_accuracy=0.75,
                failure_code="planner-output-contract-violated",
            )
            _write_report(second_path, case_accuracy=1.0, failure_code=None)

            aggregate = aggregate_planner_evaluation_reports(
                (first_path, second_path)
            )

        self.assertEqual(2, aggregate.run_count)
        self.assertEqual("qwen-openai-compatible:qwen3.8-27b", aggregate.planner_identity)
        self.assertEqual("ticket-lookup-planner-prompt-v1", aggregate.prompt_version)
        self.assertEqual(0.875, aggregate.average_case_accuracy)
        self.assertEqual(0.75, aggregate.minimum_case_accuracy)
        self.assertEqual(
            {"planner-output-contract-violated": 1},
            aggregate.failure_code_counts,
        )

    def test_rejects_reports_from_different_prompt_versions(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first_path = directory / "first.json"
            second_path = directory / "second.json"
            _write_report(first_path, case_accuracy=1.0, failure_code=None)
            _write_report(
                second_path,
                case_accuracy=1.0,
                failure_code=None,
                prompt_version="ticket-lookup-planner-prompt-v2",
            )

            with self.assertRaisesRegex(
                PlannerEvaluationAggregationError,
                "prompt_version",
            ):
                aggregate_planner_evaluation_reports((first_path, second_path))


def _write_report(
    path: Path,
    *,
    case_accuracy: float,
    failure_code: str | None,
    prompt_version: str = "ticket-lookup-planner-prompt-v1",
) -> None:
    path.write_text(
        json.dumps(
            {
                "planner_identity": "qwen-openai-compatible:qwen3.8-27b",
                "prompt_version": prompt_version,
                "dataset_id": "serviceflow-ticket-planner-v1",
                "dataset_version": 1,
                "dataset_sha256": "dataset-hash",
                "decision_accuracy": case_accuracy,
                "ticket_id_accuracy": 1.0,
                "case_accuracy": case_accuracy,
                "cases": [{"failure_code": failure_code}],
            }
        ),
        encoding="utf-8",
    )
