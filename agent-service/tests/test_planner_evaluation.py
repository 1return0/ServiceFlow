from __future__ import annotations

from unittest import TestCase
from uuid import UUID

from app.application.planner_evaluation import (
    PlannerEvaluationCase,
    PlannerEvaluator,
)
from app.domain.ticket_lookup_plan import (
    RuleBasedTicketLookupPlanner,
    TicketLookupPlan,
)


class _AlwaysRefusePlanner:
    def plan(self, *, user_query: str) -> TicketLookupPlan:
        return TicketLookupPlan(decision="refuse", reason="test refusal")


class _UnavailablePlanner:
    def plan(self, *, user_query: str) -> TicketLookupPlan:
        raise ConnectionError("model endpoint is unavailable")


class PlannerEvaluationTest(TestCase):
    ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")

    def test_scores_the_rule_based_baseline_against_fixed_cases(self) -> None:
        summary = PlannerEvaluator().evaluate(
            RuleBasedTicketLookupPlanner(),
            (
                PlannerEvaluationCase(
                    case_id="uuid-present",
                    user_query=f"查询工单 {self.ticket_id}",
                    expected_decision="lookup_ticket",
                    expected_ticket_id=self.ticket_id,
                ),
                PlannerEvaluationCase(
                    case_id="uuid-missing",
                    user_query="帮我查询工单状态",
                    expected_decision="refuse",
                ),
            ),
        )

        self.assertEqual(2, summary.total_cases)
        self.assertEqual(2, summary.passed_cases)
        self.assertEqual(1.0, summary.decision_accuracy)
        self.assertEqual(1, summary.ticket_id_evaluated_cases)
        self.assertEqual(1.0, summary.ticket_id_accuracy)
        self.assertEqual(1.0, summary.case_accuracy)

    def test_keeps_the_failed_case_for_diagnosis(self) -> None:
        summary = PlannerEvaluator().evaluate(
            _AlwaysRefusePlanner(),
            (
                PlannerEvaluationCase(
                    case_id="model-missed-uuid",
                    user_query=f"查询工单 {self.ticket_id}",
                    expected_decision="lookup_ticket",
                    expected_ticket_id=self.ticket_id,
                ),
            ),
        )

        result = summary.results[0]
        self.assertFalse(result.passed)
        self.assertEqual("lookup_ticket", result.expected_decision)
        self.assertEqual("refuse", result.actual_plan.decision)
        self.assertEqual(1, summary.ticket_id_evaluated_cases)
        self.assertEqual(0.0, summary.ticket_id_accuracy)
        self.assertEqual(0.0, summary.case_accuracy)

    def test_does_not_report_ticket_id_accuracy_without_lookup_cases(self) -> None:
        summary = PlannerEvaluator().evaluate(
            RuleBasedTicketLookupPlanner(),
            (
                PlannerEvaluationCase(
                    case_id="refusal-only",
                    user_query="帮我查询工单状态",
                    expected_decision="refuse",
                ),
            ),
        )

        self.assertEqual(0, summary.ticket_id_evaluated_cases)
        self.assertIsNone(summary.ticket_id_accuracy)

    def test_keeps_running_when_one_planner_call_is_unavailable(self) -> None:
        summary = PlannerEvaluator().evaluate(
            _UnavailablePlanner(),
            (
                PlannerEvaluationCase(
                    case_id="unavailable-model",
                    user_query="查询工单",
                    expected_decision="refuse",
                ),
            ),
        )

        result = summary.results[0]
        self.assertFalse(result.passed)
        self.assertIsNone(result.actual_plan)
        self.assertEqual("planner-exception:ConnectionError", result.failure_code)
        self.assertEqual(0.0, summary.case_accuracy)

    def test_rejects_an_invalid_golden_case_before_running_a_planner(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected_ticket_id"):
            PlannerEvaluationCase(
                case_id="invalid-golden-case",
                user_query="查询工单",
                expected_decision="lookup_ticket",
            )
