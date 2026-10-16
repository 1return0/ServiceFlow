from __future__ import annotations

from unittest import TestCase
from uuid import UUID

from app.application.agent.ticket_specialist_agent import (
    TicketAuthorizationRequiredError,
    TicketSpecialistAgent,
)
from app.infrastructure.clients.business_client import BusinessTicket


TICKET_ID = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")


class TicketSpecialistAgentTest(TestCase):
    def test_delegates_an_authorised_lookup_to_its_single_tool(self) -> None:
        tool = _RecordingTicketLookupTool()
        agent = TicketSpecialistAgent(tool)

        ticket = agent.lookup(ticket_id=TICKET_ID, authorization="Bearer student")

        self.assertEqual(TICKET_ID, ticket.id)
        self.assertEqual([(TICKET_ID, "Bearer student")], tool.calls)

    def test_rejects_an_anonymous_lookup_before_calling_the_tool(self) -> None:
        tool = _RecordingTicketLookupTool()
        agent = TicketSpecialistAgent(tool)

        with self.assertRaises(TicketAuthorizationRequiredError):
            agent.lookup(ticket_id=TICKET_ID, authorization=None)

        self.assertEqual([], tool.calls)


class _RecordingTicketLookupTool:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    def invoke(self, arguments: dict, *, authorization: str) -> BusinessTicket:
        ticket_id = arguments["ticket_id"]
        self.calls.append((ticket_id, authorization))
        return BusinessTicket(
            id=ticket_id,
            requesterReference="student-001",
            category="campus_network",
            summary="Campus network issue",
            status="SUBMITTED",
            submittedAt="2026-09-07T09:00:00Z",
            version=0,
        )
