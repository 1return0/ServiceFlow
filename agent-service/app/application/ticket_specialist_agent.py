from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.application.ticket_lookup_tool import TicketLookupTool
from app.infrastructure.business_client import BusinessTicket


class TicketAuthorizationRequiredError(PermissionError):
    """The ticket specialist cannot access protected ticket data anonymously."""


class TicketSpecialist(Protocol):
    """A bounded worker that owns protected ticket lookup capability."""

    @property
    def identity(self) -> str:
        ...

    def lookup(
        self,
        *,
        ticket_id: UUID,
        authorization: str | None,
    ) -> BusinessTicket:
        ...


class TicketSpecialistAgent:
    """Specialised Agent worker for authorised Java ticket-service access."""

    identity = "ticket-specialist-agent-v1"

    def __init__(self, ticket_lookup_tool: TicketLookupTool) -> None:
        self._ticket_lookup_tool = ticket_lookup_tool

    def lookup(
        self,
        *,
        ticket_id: UUID,
        authorization: str | None,
    ) -> BusinessTicket:
        if authorization is None or not authorization.strip():
            raise TicketAuthorizationRequiredError(
                "ticket lookup requires an authorization header"
            )
        return self._ticket_lookup_tool.execute(
            ticket_id=ticket_id,
            authorization=authorization,
        )
