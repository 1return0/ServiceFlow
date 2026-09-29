import unittest
from uuid import UUID

from pydantic import ValidationError

from app.domain.triage_plan import RuleBasedTriagePlanner, TriagePlan


class TriagePlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RuleBasedTriagePlanner()

    def test_routes_a_ticket_id_to_ticket_lookup(self) -> None:
        plan = self.planner.plan(
            user_query="查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77"
        )

        self.assertEqual("lookup_ticket", plan.decision)
        self.assertEqual(UUID("009e3cce-8f4d-448d-a060-6ce2624eac77"), plan.ticket_id)

    def test_routes_a_normal_question_to_public_support_knowledge(self) -> None:
        plan = self.planner.plan(user_query="校园网连接失败怎么办？")

        self.assertEqual("answer_support_knowledge", plan.decision)
        self.assertIsNone(plan.ticket_id)

    def test_refuses_a_blank_question(self) -> None:
        plan = self.planner.plan(user_query="   ")

        self.assertEqual("refuse", plan.decision)
        self.assertIsNone(plan.ticket_id)

    def test_handoffs_a_high_risk_question_even_when_it_contains_a_ticket_id(self) -> None:
        plan = self.planner.plan(
            user_query=(
                "教室投影仪冒烟，关联工单 "
                "009e3cce-8f4d-448d-a060-6ce2624eac77"
            )
        )

        self.assertEqual("handoff_to_human", plan.decision)
        self.assertIsNone(plan.ticket_id)
        self.assertEqual("physical_safety_risk", plan.handoff_reason)

    def test_rejects_a_knowledge_decision_with_ticket_id(self) -> None:
        with self.assertRaises(ValidationError):
            TriagePlan(
                decision="answer_support_knowledge",
                reason="invalid mixed arguments",
                ticket_id="009e3cce-8f4d-448d-a060-6ce2624eac77",
            )

    def test_rejects_follow_up_knowledge_without_ticket_lookup(self) -> None:
        with self.assertRaises(ValidationError):
            TriagePlan(
                decision="answer_support_knowledge",
                reason="invalid follow-up",
                follow_up_knowledge=True,
            )


if __name__ == "__main__":
    unittest.main()
