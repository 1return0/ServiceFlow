from __future__ import annotations

from app.application.agent_tool_planning import (
    AgentToolDefinition, AgentToolRegistry, TOOL_PLANNER_SYSTEM_PROMPT, default_tool_definitions,
)
from app.application.model_ticket_lookup_planner import PlannerCompletionModel
from app.domain.triage_plan import TriagePlan


class TriagePlannerOutputError(RuntimeError):
    """A model response could not satisfy the fixed triage JSON contract."""

    failure_code = "triage-output-contract-violated"


class ModelTriagePlanner:
    """Converts a model completion into a strictly validated triage decision."""

    prompt_version = "campus-support-triage-prompt-v6"
    system_prompt = TOOL_PLANNER_SYSTEM_PROMPT

    def __init__(self, model: PlannerCompletionModel,
                 tools: tuple[AgentToolDefinition, ...] | None = None) -> None:
        self._model = model
        self._registry = AgentToolRegistry(default_tool_definitions() if tools is None else tools)

    @property
    def identity(self) -> str:
        return self._model.identity

    def plan(self, *, user_query: str) -> TriagePlan:
        raw_response = self._model.complete(
            system_prompt=self.system_prompt,
            user_query=self._registry.prompt_payload(user_query),
        )
        try:
            return self._registry.decode(raw_response)
        except (ValueError, TypeError) as error:
            raise TriagePlannerOutputError(
                "model response violated the campus-support triage contract"
            ) from error

    def close(self) -> None:
        close = getattr(self._model, "close", None)
        if callable(close):
            close()
