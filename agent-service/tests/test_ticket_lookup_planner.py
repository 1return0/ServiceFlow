import unittest
from uuid import UUID

from app.domain.ticket_lookup_plan import RuleBasedTicketLookupPlanner


class RuleBasedTicketLookupPlannerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RuleBasedTicketLookupPlanner()

    def test_selects_lookup_when_a_ticket_id_is_present(self) -> None:
        plan = self.planner.plan(
            user_query="请查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77"
        )

        self.assertEqual("lookup_ticket", plan.decision)
        self.assertEqual(
            UUID("009e3cce-8f4d-448d-a060-6ce2624eac77"),
            plan.ticket_id,
        )

    def test_refuses_when_no_ticket_id_is_present(self) -> None:
        plan = self.planner.plan(user_query="帮我看看工单进度")

        self.assertEqual("refuse", plan.decision)
        self.assertIsNone(plan.ticket_id)


if __name__ == "__main__":
    unittest.main()
