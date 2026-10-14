from __future__ import annotations

from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.business_client import BusinessServiceClient, BusinessTicket


class TicketLookupArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_id: UUID = Field(description="Complete UUID of the ticket explicitly requested by the user.")


class TicketLookupTool:
    """Read one ticket through the authoritative Java business-service boundary."""

    name = "lookup_ticket"
    description = "Read a requested ticket through Java's ownership and role checks. Requires a complete ticket UUID."
    arguments_model = TicketLookupArguments
    routing_decision = "lookup_ticket"

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return self.arguments_model.model_json_schema()

    def invoke(self, raw_arguments: dict[str, Any], *, authorization: str) -> BusinessTicket:
        arguments = self.arguments_model.model_validate(raw_arguments)
        return self.execute(ticket_id=arguments.ticket_id, authorization=authorization)

    def __init__(self, business_service_client: BusinessServiceClient) -> None:
        self._business_service_client = business_service_client

    def execute(
        self,
        *,
        ticket_id: UUID,
        authorization: str,
    ) -> BusinessTicket:
        arguments = self.arguments_model(ticket_id=ticket_id)
        return self._business_service_client.get_ticket(
            arguments.ticket_id,
            authorization=authorization,
        )
