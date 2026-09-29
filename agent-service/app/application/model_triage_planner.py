from __future__ import annotations

import json

from pydantic import ValidationError

from app.application.model_ticket_lookup_planner import PlannerCompletionModel
from app.domain.triage_plan import TriagePlan


class TriagePlannerOutputError(RuntimeError):
    """A model response could not satisfy the fixed triage JSON contract."""

    failure_code = "triage-output-contract-violated"


class ModelTriagePlanner:
    """Converts a model completion into a strictly validated triage decision."""

    prompt_version = "campus-support-triage-prompt-v5"
    system_prompt = """
You are a campus-support triage planner. Return JSON only, with these required keys:
decision, reason, ticket_id, follow_up_knowledge. Add handoff_reason only for handoff_to_human.
decision must be lookup_ticket, get_notification_summary, answer_support_knowledge, handoff_to_human, or refuse.
Select lookup_ticket only when the user query contains one complete UUID ticket ID.
Select get_notification_summary only when the user asks for their unread notification count or notification summary.
Select answer_support_knowledge for public campus IT or teaching-service questions.
For immediate account-security or physical-safety risks, select handoff_to_human even when
the query contains a ticket ID. Examples include account compromise, smoke, fire,
electric shock, or electrical leakage.
For handoff_to_human, ticket_id must be null and handoff_reason must be one of
account_security_risk or physical_safety_risk. For all other decisions, handoff_reason
must be null. For answer_support_knowledge and refuse, ticket_id must be null.
Do not answer the user's question and do not invent a ticket ID.
Set follow_up_knowledge=true only when a ticket lookup is needed and the user also asks
for general next-step guidance. Otherwise it must be false.
""".strip()

    def __init__(self, model: PlannerCompletionModel) -> None:
        self._model = model

    @property
    def identity(self) -> str:
        return self._model.identity

    def plan(self, *, user_query: str) -> TriagePlan:
        raw_response = self._model.complete(
            system_prompt=self.system_prompt,
            user_query=user_query,
        )
        try:
            payload = json.loads(raw_response)
            return TriagePlan.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise TriagePlannerOutputError(
                "model response violated the campus-support triage contract"
            ) from error

    def close(self) -> None:
        close = getattr(self._model, "close", None)
        if callable(close):
            close()
