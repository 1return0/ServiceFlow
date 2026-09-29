from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.planner_evaluation_runner import (
    run_planner_evaluation,
    write_planner_evaluation_report,
)
from app.domain.ticket_lookup_plan import RuleBasedTicketLookupPlanner


class PlannerEvaluationRunnerTest(TestCase):
    def test_builds_a_traceable_report_from_the_fixed_dataset(self) -> None:
        report = run_planner_evaluation(
            planner=RuleBasedTicketLookupPlanner(),
            dataset_path=Path("data/planner-evaluation/planner-eval-v1.json"),
            evaluated_at=datetime(2026, 9, 3, tzinfo=UTC),
        )

        self.assertEqual("rule-based-ticket-id-v1", report.planner_identity)
        self.assertIsNone(report.prompt_version)
        self.assertEqual("serviceflow-ticket-planner-v1", report.dataset_id)
        self.assertEqual(4, report.total_cases)
        self.assertEqual(1.0, report.case_accuracy)
        self.assertEqual(2, report.ticket_id_evaluated_cases)
        self.assertEqual(4, len(report.cases))

    def test_writes_once_without_overwriting_an_existing_report(self) -> None:
        report = run_planner_evaluation(
            planner=RuleBasedTicketLookupPlanner(),
            dataset_path=Path("data/planner-evaluation/planner-eval-v1.json"),
        )
        with TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "rule-based-v1.json"
            write_planner_evaluation_report(report, output_path)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual("rule-based-ticket-id-v1", payload["planner_identity"])
            with self.assertRaises(FileExistsError):
                write_planner_evaluation_report(report, output_path)
