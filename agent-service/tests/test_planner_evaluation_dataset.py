from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.evaluation.planner_evaluation_dataset import (
    PlannerEvaluationDatasetError,
    load_planner_evaluation_dataset,
)


class PlannerEvaluationDatasetTest(TestCase):
    def test_loads_the_versioned_golden_dataset_with_a_fingerprint(self) -> None:
        dataset = load_planner_evaluation_dataset(
            Path("data/planner-evaluation/planner-eval-v1.json")
        )

        self.assertEqual("serviceflow-ticket-planner-v1", dataset.dataset_id)
        self.assertEqual(1, dataset.dataset_version)
        self.assertEqual(4, len(dataset.cases))
        self.assertEqual(64, len(dataset.dataset_sha256))

    def test_rejects_a_dataset_with_an_invalid_lookup_case(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.json"
            path.write_text(
                json.dumps(
                    {
                        "dataset_id": "invalid",
                        "dataset_version": 1,
                        "cases": [
                            {
                                "case_id": "missing-id",
                                "user_query": "查询工单",
                                "expected_decision": "lookup_ticket",
                                "expected_ticket_id": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(PlannerEvaluationDatasetError):
                load_planner_evaluation_dataset(path)
