from __future__ import annotations

from unittest import TestCase

from fastapi.testclient import TestClient

from fastapi import FastAPI

from app.api.routes import create_router
from app.bootstrap import build_application_lifespan
from app.config import Settings


class CampusSupportTriageApiTest(TestCase):
    def setUp(self) -> None:
        settings = Settings()
        app = FastAPI(lifespan=build_application_lifespan(settings))
        app.include_router(create_router(settings))
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_answers_public_knowledge_without_a_bearer_token(self) -> None:
        response = self.client.post(
            "/api/v1/agent/triage",
            json={"user_query": "校园网连接失败怎么办？"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("answer_support_knowledge", payload["decision"])
        self.assertIsNone(payload["ticket"])
        self.assertEqual("answered", payload["knowledge_answer"]["status"])
        self.assertTrue(payload["trace"]["request_id"])
        self.assertEqual(
            ["triage", "route_after_triage", "answer_support_knowledge"],
            [step["node"] for step in payload["trace"]["steps"]],
        )
        self.assertNotIn("user_query", str(payload["trace"]))

    def test_rejects_a_ticket_branch_without_a_bearer_token(self) -> None:
        response = self.client.post(
            "/api/v1/agent/triage",
            json={
                "user_query": (
                    "查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77"
                )
            },
        )

        self.assertEqual(401, response.status_code)
        self.assertEqual("Bearer token is required", response.json()["detail"])

    def test_rejects_a_blank_question_before_invoking_the_graph(self) -> None:
        response = self.client.post(
            "/api/v1/agent/triage",
            json={"user_query": "   "},
        )

        self.assertEqual(422, response.status_code)

    def test_handoffs_a_high_risk_question_without_calling_a_tool(self) -> None:
        response = self.client.post(
            "/api/v1/agent/triage",
            json={"user_query": "教室投影仪冒烟怎么办？"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("handoff_to_human", payload["decision"])
        self.assertEqual("physical_safety_risk", payload["handoff_reason"])
        self.assertEqual(
            "physical_safety_risk", payload["handoff_guidance"]["reason"]
        )
        self.assertIn("停止使用", payload["handoff_guidance"]["title"])
        self.assertIsNone(payload["ticket"])
        self.assertIsNone(payload["knowledge_answer"])

    def test_returns_account_specific_handoff_guidance(self) -> None:
        response = self.client.post(
            "/api/v1/agent/triage",
            json={"user_query": "我的账号被盗了怎么办？"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("handoff_to_human", payload["decision"])
        self.assertEqual("account_security_risk", payload["handoff_reason"])
        self.assertIn("账号安全", payload["handoff_guidance"]["title"])
        self.assertIn("修改密码", payload["handoff_guidance"]["immediate_actions"][1])


if __name__ == "__main__":
    import unittest

    unittest.main()
