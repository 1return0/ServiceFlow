import unittest

from app.application.agent.handoff_guard import CampusRiskHandoffGuard


class CampusRiskHandoffGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = CampusRiskHandoffGuard()

    def test_detects_account_security_risk(self) -> None:
        self.assertEqual(
            "account_security_risk",
            self.guard.detect(user_query="我的校园账号被盗了，怎么办？"),
        )

    def test_detects_physical_safety_risk(self) -> None:
        self.assertEqual(
            "physical_safety_risk",
            self.guard.detect(user_query="机房插座冒烟了"),
        )

    def test_does_not_handoff_normal_knowledge_question(self) -> None:
        self.assertIsNone(
            self.guard.detect(user_query="校园网密码忘记了怎么办？"),
        )


if __name__ == "__main__":
    unittest.main()
