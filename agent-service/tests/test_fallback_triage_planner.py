from unittest import TestCase

from app.application.fallback_triage_planner import FallbackTriagePlanner
from app.application.model_triage_planner import TriagePlannerOutputError
from app.domain.triage_plan import RuleBasedTriagePlanner, TriagePlan
from app.infrastructure.qwen_openai_planner_model import PlannerModelUnavailableError


class FailingPrimaryPlanner:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.calls = 0

    @property
    def identity(self) -> str:
        return "failing-model-triage"

    def plan(self, *, user_query: str) -> TriagePlan:
        self.calls += 1
        raise self._error


class FallbackTriagePlannerTest(TestCase):
    def test_falls_back_for_a_temporary_model_timeout(self) -> None:
        primary = FailingPrimaryPlanner(
            PlannerModelUnavailableError("planner-model-timeout")
        )
        planner = FallbackTriagePlanner(primary, RuleBasedTriagePlanner())

        plan = planner.plan(user_query="校园网连接失败怎么办？")

        self.assertEqual("answer_support_knowledge", plan.decision)
        self.assertEqual(1, primary.calls)

    def test_falls_back_when_model_output_violates_the_contract(self) -> None:
        planner = FallbackTriagePlanner(
            FailingPrimaryPlanner(TriagePlannerOutputError("invalid JSON plan")),
            RuleBasedTriagePlanner(),
        )

        plan = planner.plan(user_query="查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77")

        self.assertEqual("lookup_ticket", plan.decision)
        self.assertIsNotNone(plan.ticket_id)

    def test_does_not_hide_model_authentication_failure(self) -> None:
        planner = FallbackTriagePlanner(
            FailingPrimaryPlanner(
                PlannerModelUnavailableError("planner-model-authentication-failed")
            ),
            RuleBasedTriagePlanner(),
        )

        with self.assertRaises(PlannerModelUnavailableError):
            planner.plan(user_query="校园网连接失败怎么办？")


if __name__ == "__main__":
    import unittest

    unittest.main()
