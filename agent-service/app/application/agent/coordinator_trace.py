from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable
from uuid import uuid4


@dataclass(frozen=True)
class CoordinatorTraceStep:
    node: str
    specialist_identity: str | None
    tool_name: str | None
    elapsed_seconds: float
    status: str
    decision: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class CoordinatorTrace:
    request_id: str
    steps: tuple[CoordinatorTraceStep, ...]


class CoordinatorTraceRecorder:
    """Per-invocation trace recorder; deliberately excludes request/token/body data."""

    def __init__(self) -> None:
        self._request_id = str(uuid4())
        self._steps: list[CoordinatorTraceStep] = []

    @property
    def request_id(self) -> str:
        return self._request_id

    def capture[T](
        self,
        *,
        node: str,
        specialist_identity: str | None,
        tool_name: str | None,
        operation: Callable[[], T],
        decision: str | None = None,
    ) -> T:
        started_at = perf_counter()
        try:
            result = operation()
        except Exception as error:
            self._steps.append(
                CoordinatorTraceStep(
                    node=node,
                    specialist_identity=specialist_identity,
                    tool_name=tool_name,
                    elapsed_seconds=perf_counter() - started_at,
                    status="failed",
                    decision=decision,
                    failure_code=_failure_code(error),
                )
            )
            raise
        self._steps.append(
            CoordinatorTraceStep(
                node=node,
                specialist_identity=specialist_identity,
                tool_name=tool_name,
                elapsed_seconds=perf_counter() - started_at,
                status="succeeded",
                decision=decision,
            )
        )
        return result

    def snapshot(self) -> CoordinatorTrace:
        return CoordinatorTrace(self._request_id, tuple(self._steps))

    def record_route(self, decision: str) -> None:
        self._steps.append(
            CoordinatorTraceStep(
                node="route_after_triage",
                specialist_identity="campus-support-coordinator-v1",
                tool_name=None,
                elapsed_seconds=0.0,
                status="succeeded",
                decision=decision,
            )
        )


def _failure_code(error: Exception) -> str:
    return {
        "TicketAuthorizationRequiredError": "ticket-authorization-required",
        "BusinessServiceUnavailableError": "business-service-unavailable",
        "BusinessServiceResponseError": "business-service-response-rejected",
        "ValueError": "workflow-contract-invalid",
    }.get(type(error).__name__, "unexpected-runtime-error")
