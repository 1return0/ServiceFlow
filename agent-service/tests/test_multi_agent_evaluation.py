from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

from app.application.evaluation.multi_agent_evaluation import (
    MultiAgentEvaluationCase,
    MultiAgentEvaluator,
)
from app.application.evaluation.multi_agent_evaluation_dataset import (
    load_multi_agent_evaluation_dataset,
)


@dataclass(frozen=True)
class _Step:
    node: str


@dataclass(frozen=True)
class _Trace:
    steps: tuple[_Step, ...]


class _FixedInvoker:
    def invoke(self, *, user_query: str, authorization: str | None = None) -> dict[str, object]:
        return {
            "decision": "lookup_ticket",
            "trace": _Trace((_Step("triage"), _Step("route_after_triage"), _Step("lookup_ticket"))),
        }


class _UnavailableError(RuntimeError):
    failure_code = "business-service-unavailable"


class _UnavailableInvoker:
    def invoke(self, *, user_query: str, authorization: str | None = None) -> dict[str, object]:
        raise _UnavailableError()


class MultiAgentEvaluationTest(TestCase):
    def test_scores_decision_route_and_whole_case_separately(self) -> None:
        summary = MultiAgentEvaluator().evaluate(
            _FixedInvoker(),
            (
                MultiAgentEvaluationCase(
                    case_id="correct",
                    user_query="query",
                    expected_decision="lookup_ticket",
                    expected_required_nodes=("triage", "route_after_triage", "lookup_ticket"),
                ),
                MultiAgentEvaluationCase(
                    case_id="wrong-route",
                    user_query="query",
                    expected_decision="lookup_ticket",
                    expected_required_nodes=("triage", "answer_support_knowledge"),
                ),
            ),
        )

        self.assertEqual(1.0, summary.decision_accuracy)
        self.assertEqual(0.5, summary.route_accuracy)
        self.assertEqual(0.5, summary.case_accuracy)

    def test_accepts_an_expected_dependency_failure_without_calling_it_a_successful_route(self) -> None:
        summary = MultiAgentEvaluator().evaluate(
            _UnavailableInvoker(),
            (
                MultiAgentEvaluationCase(
                    case_id="dependency-down",
                    user_query="query",
                    expected_decision=None,
                    expected_required_nodes=("triage", "route_after_triage", "lookup_ticket"),
                    expected_failure_code="business-service-unavailable",
                ),
            ),
        )

        self.assertEqual(1.0, summary.case_accuracy)
        self.assertIsNone(summary.decision_accuracy)
        self.assertIsNone(summary.route_accuracy)

    def test_loads_the_frozen_dataset_with_a_content_hash(self) -> None:
        dataset = load_multi_agent_evaluation_dataset(
            Path("data/multi-agent-evaluation/campus-support-triage-v1.json")
        )

        self.assertEqual("serviceflow-campus-support-triage-v1", dataset.dataset_id)
        self.assertEqual(7, len(dataset.cases))
        self.assertEqual(64, len(dataset.dataset_sha256))
