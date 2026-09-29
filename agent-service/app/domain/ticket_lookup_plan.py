from __future__ import annotations

import re
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, model_validator


class TicketLookupPlan(BaseModel):
    decision: Literal["lookup_ticket", "refuse"]
    reason: str
    ticket_id: UUID | None = None

    @model_validator(mode="after")
    def validate_decision_arguments(self) -> "TicketLookupPlan":
        if self.decision == "lookup_ticket" and self.ticket_id is None:
            raise ValueError("lookup_ticket decision requires ticket_id")
        if self.decision == "refuse" and self.ticket_id is not None:
            raise ValueError("refuse decision must not contain ticket_id")
        return self


class TicketLookupPlanner(Protocol):
    def plan(self, *, user_query: str) -> TicketLookupPlan:
        ...


class RuleBasedTicketLookupPlanner:
    """Deterministic baseline before replacing planning with a model-backed adapter."""

    _TICKET_ID_PATTERN = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )

    @property
    def identity(self) -> str:
        return "rule-based-ticket-id-v1"

    def plan(self, *, user_query: str) -> TicketLookupPlan:
        match = self._TICKET_ID_PATTERN.search(user_query)
        if match is None:
            return TicketLookupPlan(
                decision="refuse",
                reason="ticket_id is required for a deterministic ticket lookup",
            )
        return TicketLookupPlan(
            decision="lookup_ticket",
            reason="a ticket_id was found in the user query",
            ticket_id=UUID(match.group()),
        )
