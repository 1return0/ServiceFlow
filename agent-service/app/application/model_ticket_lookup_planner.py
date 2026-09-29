from __future__ import annotations

import json
from typing import Protocol

from pydantic import ValidationError

from app.domain.ticket_lookup_plan import TicketLookupPlan


class PlannerCompletionModel(Protocol):
    """Minimal model boundary: the planner needs text completion, not an SDK type."""

    @property
    def identity(self) -> str:
        ...

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        ...


class PlannerOutputError(RuntimeError):
    """A model response could not satisfy the fixed planner JSON contract."""

    failure_code = "planner-output-contract-violated"


class ModelTicketLookupPlanner:
    """Converts a model completion into a strictly validated ticket lookup plan."""

    prompt_version = "ticket-lookup-planner-prompt-v1"
    system_prompt = """
You are a ticket lookup planner. Return JSON only, with exactly these keys:
decision, reason, ticket_id.
decision must be lookup_ticket or refuse.
Select lookup_ticket only when the user query contains one complete UUID ticket ID.
For refuse, ticket_id must be null.
Do not answer the user's question and do not invent a ticket ID.
""".strip()

    def __init__(self, model: PlannerCompletionModel) -> None:
        self._model = model

    @property
    def identity(self) -> str:
        return self._model.identity

    def plan(self, *, user_query: str) -> TicketLookupPlan:
        raw_response = self._model.complete(
            system_prompt=self.system_prompt,
            user_query=user_query,
        )
        try:
            payload = json.loads(raw_response)
            return TicketLookupPlan.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise PlannerOutputError(
                "model response violated the ticket lookup plan contract"
            ) from error

    def close(self) -> None:
        close = getattr(self._model, "close", None)
        if callable(close):
            close()
