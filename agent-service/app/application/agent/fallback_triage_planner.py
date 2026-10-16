from __future__ import annotations

from app.application.agent.model_triage_planner import TriagePlannerOutputError
from app.domain.triage_plan import TriagePlan, TriagePlanner
from app.infrastructure.models.qwen_openai_planner_model import PlannerModelUnavailableError


_FALLBACK_ELIGIBLE_FAILURE_CODES = frozenset(
    {
        "planner-model-timeout",
        "planner-model-network-error",
        "planner-model-rate-limited",
        "planner-model-server-error",
        "planner-model-invalid-response",
    }
)


class FallbackTriagePlanner:
    """Uses a deterministic planner only for safe, bounded model failures."""

    def __init__(
        self,
        primary: TriagePlanner,
        fallback: TriagePlanner,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def identity(self) -> str:
        return f"fallback({self._primary.identity}->{self._fallback.identity})"

    def plan(self, *, user_query: str) -> TriagePlan:
        try:
            return self._primary.plan(user_query=user_query)
        except TriagePlannerOutputError:
            return self._fallback.plan(user_query=user_query)
        except PlannerModelUnavailableError as error:
            if error.failure_code not in _FALLBACK_ELIGIBLE_FAILURE_CODES:
                raise
            return self._fallback.plan(user_query=user_query)

    def close(self) -> None:
        self._close_planner(self._primary)
        if self._fallback is not self._primary:
            self._close_planner(self._fallback)

    @staticmethod
    def _close_planner(planner: TriagePlanner) -> None:
        close = getattr(planner, "close", None)
        if callable(close):
            close()
