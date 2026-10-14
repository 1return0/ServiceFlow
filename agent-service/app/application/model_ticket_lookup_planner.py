from __future__ import annotations

from typing import Protocol
from app.application.agent_tool_planning import (
    AgentToolDefinition, AgentToolRegistry, TOOL_PLANNER_SYSTEM_PROMPT,
)
from app.application.ticket_lookup_tool import TicketLookupTool

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

    prompt_version = "ticket-lookup-planner-prompt-v2"
    system_prompt = TOOL_PLANNER_SYSTEM_PROMPT

    def __init__(self, model: PlannerCompletionModel) -> None:
        self._model = model
        self._registry = AgentToolRegistry((AgentToolDefinition.from_tool(TicketLookupTool),))

    @property
    def identity(self) -> str:
        return self._model.identity

    def plan(self, *, user_query: str) -> TicketLookupPlan:
        raw_response = self._model.complete(
            system_prompt=self.system_prompt,
            user_query=self._registry.prompt_payload(user_query),
        )
        try:
            plan = self._registry.decode(raw_response)
            return TicketLookupPlan(decision=plan.decision, reason=plan.reason, ticket_id=plan.ticket_id)
        except (ValueError, TypeError) as error:
            raise PlannerOutputError(
                "model response violated the ticket lookup plan contract"
            ) from error

    def close(self) -> None:
        close = getattr(self._model, "close", None)
        if callable(close):
            close()
