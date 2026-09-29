from unittest import TestCase

from app.application.handoff_guidance import get_handoff_guidance


class HandoffGuidanceTest(TestCase):
    def test_returns_account_specific_guidance(self) -> None:
        guidance = get_handoff_guidance("account_security_risk")

        self.assertEqual("account_security_risk", guidance.reason)
        self.assertIn("账号安全", guidance.title)
        self.assertIn("修改密码", guidance.immediate_actions[1])

    def test_returns_physical_safety_specific_guidance(self) -> None:
        guidance = get_handoff_guidance("physical_safety_risk")

        self.assertEqual("physical_safety_risk", guidance.reason)
        self.assertIn("停止使用", guidance.title)
        self.assertIn("远离", guidance.immediate_actions[0])
