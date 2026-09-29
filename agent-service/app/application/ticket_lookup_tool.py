from __future__ import annotations

from uuid import UUID

from app.infrastructure.business_client import BusinessServiceClient, BusinessTicket


class TicketLookupTool:
    """Read one ticket through the authoritative Java business-service boundary."""

    name = "lookup_ticket"

    def __init__(self, business_service_client: BusinessServiceClient) -> None:
        self._business_service_client = business_service_client

    def execute(
        self,
        *,
        ticket_id: UUID,
        authorization: str,
    ) -> BusinessTicket:
        return self._business_service_client.get_ticket(
            ticket_id,
            authorization=authorization,
        )
