import unittest
from uuid import UUID

from app.infrastructure.business_client import BusinessTicket
from app.application.ticket_lookup_tool import TicketLookupTool


class StubBusinessServiceClient:
    def __init__(self, ticket: BusinessTicket) -> None:
        self.ticket = ticket
        self.received_ticket_id: UUID | None = None
        self.received_authorization: str | None = None

    def get_ticket(self, ticket_id: UUID, *, authorization: str) -> BusinessTicket:
        self.received_ticket_id = ticket_id
        self.received_authorization = authorization
        return self.ticket


class TicketLookupToolTest(unittest.TestCase):
    def test_executes_through_the_business_service_client(self) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        ticket = BusinessTicket(
            id=ticket_id,
            requesterReference="stu-db-smoke-001",
            category="CAMPUS_NETWORK",
            summary="Database authentication smoke ticket",
            submittedAt="2026-08-31T00:00:00Z",
            status="IN_PROGRESS",
            version=1,
        )
        client = StubBusinessServiceClient(ticket)

        result = TicketLookupTool(client).execute(
            ticket_id=ticket_id,
            authorization="Bearer user-token",
        )

        self.assertEqual(ticket, result)
        self.assertEqual(ticket_id, client.received_ticket_id)
        self.assertEqual("Bearer user-token", client.received_authorization)


if __name__ == "__main__":
    unittest.main()
