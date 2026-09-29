import unittest
from uuid import UUID

from app.infrastructure.business_client import BusinessTicket
from app.domain.ticket_lookup_plan import RuleBasedTicketLookupPlanner
from app.application.ticket_lookup_tool import TicketLookupTool
from app.application.workflows.ticket_assistant_graph import TicketAssistantGraph


class StubBusinessServiceClient:
    def __init__(self, ticket: BusinessTicket) -> None:
        self.ticket = ticket
        self.call_count = 0

    def get_ticket(self, ticket_id: UUID, *, authorization: str) -> BusinessTicket:
        self.call_count += 1
        return self.ticket


class TicketAssistantGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        self.ticket = BusinessTicket(
            id=self.ticket_id,
            requesterReference="stu-db-smoke-001",
            category="CAMPUS_NETWORK",
            summary="Database authentication smoke ticket",
            submittedAt="2026-08-31T00:00:00Z",
            status="IN_PROGRESS",
            version=1,
        )

    def test_routes_a_planned_lookup_to_the_tool_node(self) -> None:
        client = StubBusinessServiceClient(self.ticket)
        graph = TicketAssistantGraph(
            RuleBasedTicketLookupPlanner(),
            TicketLookupTool(client),
        )

        result = graph.invoke(
            user_query=f"查询工单 {self.ticket_id}",
            authorization="Bearer user-token",
        )

        self.assertEqual("lookup_ticket", result["decision"])
        self.assertEqual(self.ticket, result["ticket"])
        self.assertEqual(1, client.call_count)

    def test_ends_without_calling_java_when_the_plan_refuses(self) -> None:
        client = StubBusinessServiceClient(self.ticket)
        graph = TicketAssistantGraph(
            RuleBasedTicketLookupPlanner(),
            TicketLookupTool(client),
        )

        result = graph.invoke(
            user_query="帮我看看工单进度",
            authorization="Bearer user-token",
        )

        self.assertEqual("refuse", result["decision"])
        self.assertIsNone(result["ticket"])
        self.assertEqual(0, client.call_count)


if __name__ == "__main__":
    unittest.main()
