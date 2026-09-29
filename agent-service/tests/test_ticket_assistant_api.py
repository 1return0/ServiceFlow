import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class TicketAssistantApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    @patch("app.api.routes.TicketAssistantGraph")
    def test_routes_a_natural_language_request_to_the_assistant_graph(
        self,
        graph_class,
    ) -> None:
        graph_class.return_value.invoke.return_value = {
            "decision": "refuse",
            "reason": "ticket_id is required for a deterministic ticket lookup",
            "ticket": None,
        }

        response = self.client.post(
            "/api/v1/agent/assist",
            headers={"Authorization": "Bearer user-token"},
            json={"user_query": "帮我看看工单进度"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("refuse", response.json()["decision"])
        graph_class.return_value.invoke.assert_called_once_with(
            user_query="帮我看看工单进度",
            authorization="Bearer user-token",
        )


if __name__ == "__main__":
    unittest.main()
