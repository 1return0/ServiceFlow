from unittest import TestCase

from app.application.agent.controlled_replanning import ControlledReplanPolicy


class ControlledReplanPolicyTest(TestCase):
    def test_allows_only_one_safe_read_replan(self) -> None:
        policy = ControlledReplanPolicy()
        self.assertEqual(
            "replan_once",
            policy.assess(
                result_code="no_matches",
                replan_count=0,
                operation_kind="read",
            ).decision,
        )
        self.assertEqual(
            "stop",
            policy.assess(
                result_code="no_matches",
                replan_count=1,
                operation_kind="read",
            ).decision,
        )

    def test_refuses_write_replanning(self) -> None:
        self.assertEqual(
            "stop",
            ControlledReplanPolicy().assess(
                result_code="insufficient_evidence",
                replan_count=0,
                operation_kind="write",
            ).decision,
        )
