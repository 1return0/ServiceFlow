import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.infrastructure.clients.business_client import BusinessTicket
from app.main import app


class TicketToolApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    @patch("app.api.routes.BusinessServiceClient")
    def test_forwards_a_bearer_authenticated_lookup_to_the_business_client(
        self,
        client_class,
    ) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        client_class.return_value.get_ticket.return_value = BusinessTicket(
            id=ticket_id,
            requesterReference="stu-db-smoke-001",
            category="CAMPUS_NETWORK",
            summary="Database authentication smoke ticket",
            submittedAt="2026-08-31T00:00:00Z",
            status="IN_PROGRESS",
            version=1,
        )

        response = self.client.post(
            "/api/v1/tools/tickets/lookup",
            headers={"Authorization": "Bearer user-token"},
            json={"ticket_id": str(ticket_id)},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(str(ticket_id), response.json()["id"])
        client_class.return_value.get_ticket.assert_called_once_with(
            ticket_id,
            authorization="Bearer user-token",
        )

    def test_rejects_a_lookup_without_bearer_token(self) -> None:
        response = self.client.post(
            "/api/v1/tools/tickets/lookup",
            json={"ticket_id": "009e3cce-8f4d-448d-a060-6ce2624eac77"},
        )

        self.assertEqual(401, response.status_code)


if __name__ == "__main__":
    unittest.main()
