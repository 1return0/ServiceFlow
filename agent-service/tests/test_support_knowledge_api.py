from __future__ import annotations

from unittest import TestCase

from fastapi.testclient import TestClient

from app.main import app


class SupportKnowledgeApiTest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_answers_a_campus_knowledge_question_with_a_source(self) -> None:
        response = self.client.post(
            "/api/v1/knowledge/answer",
            json={"question": "教学系统打不开，课程无法访问怎么办？"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("answered", payload["status"])
        self.assertFalse(payload["model_called"])
        self.assertEqual("course-system-v1", payload["citations"][0]["article_id"])

    def test_returns_insufficient_evidence_without_calling_an_external_model(self) -> None:
        response = self.client.post(
            "/api/v1/knowledge/answer",
            json={"question": "食堂今天有什么菜？"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("insufficient_evidence", payload["status"])
        self.assertEqual([], payload["citations"])

    def test_rejects_a_blank_knowledge_question(self) -> None:
        response = self.client.post(
            "/api/v1/knowledge/answer",
            json={"question": "   "},
        )

        self.assertEqual(422, response.status_code)
