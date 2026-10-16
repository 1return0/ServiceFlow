"""Per-invocation limits and safe operational trace for Agent execution."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, Generator, Literal, Protocol, TypeVar


T = TypeVar("T")
HarnessOperationKind = Literal["model", "tool"]
HarnessStepStatus = Literal["succeeded", "failed", "rejected"]
_ACTIVE_AGENT_HARNESS: ContextVar["AgentHarness | None"] = ContextVar(
    "active_agent_harness",
    default=None,
)


class CompletionModel(Protocol):
    """The small common boundary shared by planner and answer models."""

    @property
    def identity(self) -> str:
        ...

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        ...


class AgentHarnessLimitExceededError(RuntimeError):
    def __init__(self, failure_code: str) -> None:
        super().__init__(failure_code)
        self.failure_code = failure_code


@dataclass(frozen=True, slots=True)
class AgentHarnessLimits:
    max_model_calls: int = 3
    max_tool_calls: int = 4
    max_elapsed_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_model_calls < 0:
            raise ValueError("max_model_calls must not be negative")
        if self.max_tool_calls < 0:
            raise ValueError("max_tool_calls must not be negative")
        if self.max_elapsed_seconds <= 0:
            raise ValueError("max_elapsed_seconds must be positive")


@dataclass(frozen=True, slots=True)
class AgentHarnessStep:
    operation_kind: HarnessOperationKind
    operation_name: str
    status: HarnessStepStatus
    elapsed_seconds: float
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class AgentHarnessSnapshot:
    model_call_count: int
    tool_call_count: int
    elapsed_seconds: float
    steps: tuple[AgentHarnessStep, ...]


class AgentHarness:
    """Owns request-scoped limits, not business routing or authorization."""

    def __init__(
        self,
        limits: AgentHarnessLimits | None = None,
        *,
        time_source: Callable[[], float] = perf_counter,
    ) -> None:
        self._limits = limits or AgentHarnessLimits()
        self._time_source = time_source
        self._started_at = time_source()
        self._model_call_count = 0
        self._tool_call_count = 0
        self._steps: list[AgentHarnessStep] = []

    def invoke_model(self, operation_name: str, operation: Callable[[], T]) -> T:
        return self._invoke("model", operation_name, operation)

    def invoke_tool(self, operation_name: str, operation: Callable[[], T]) -> T:
        return self._invoke("tool", operation_name, operation)

    def snapshot(self) -> AgentHarnessSnapshot:
        return AgentHarnessSnapshot(
            model_call_count=self._model_call_count,
            tool_call_count=self._tool_call_count,
            elapsed_seconds=self._elapsed_seconds(),
            steps=tuple(self._steps),
        )

    def _invoke(
        self,
        operation_kind: HarnessOperationKind,
        operation_name: str,
        operation: Callable[[], T],
    ) -> T:
        if not operation_name.strip():
            raise ValueError("harness operation_name must not be blank")
        limit_failure = self._limit_failure(operation_kind)
        if limit_failure is not None:
            self._steps.append(
                AgentHarnessStep(
                    operation_kind=operation_kind,
                    operation_name=operation_name,
                    status="rejected",
                    elapsed_seconds=0.0,
                    failure_code=limit_failure,
                )
            )
            raise AgentHarnessLimitExceededError(limit_failure)

        self._increment_call_count(operation_kind)
        started_at = self._time_source()
        try:
            result = operation()
        except Exception as error:
            self._steps.append(
                AgentHarnessStep(
                    operation_kind=operation_kind,
                    operation_name=operation_name,
                    status="failed",
                    elapsed_seconds=self._time_source() - started_at,
                    failure_code=_safe_failure_code(error),
                )
            )
            raise
        self._steps.append(
            AgentHarnessStep(
                operation_kind=operation_kind,
                operation_name=operation_name,
                status="succeeded",
                elapsed_seconds=self._time_source() - started_at,
            )
        )
        return result

    def _limit_failure(self, operation_kind: HarnessOperationKind) -> str | None:
        if self._elapsed_seconds() >= self._limits.max_elapsed_seconds:
            return "harness-elapsed-time-limit-reached"
        if operation_kind == "model" and self._model_call_count >= self._limits.max_model_calls:
            return "harness-model-call-limit-reached"
        if operation_kind == "tool" and self._tool_call_count >= self._limits.max_tool_calls:
            return "harness-tool-call-limit-reached"
        return None

    def _increment_call_count(self, operation_kind: HarnessOperationKind) -> None:
        if operation_kind == "model":
            self._model_call_count += 1
        else:
            self._tool_call_count += 1

    def _elapsed_seconds(self) -> float:
        return self._time_source() - self._started_at


@contextmanager
def bind_agent_harness(harness: AgentHarness) -> Generator[None, None, None]:
    """Makes one request's harness visible to nested model adapters only."""

    token: Token[AgentHarness | None] = _ACTIVE_AGENT_HARNESS.set(harness)
    try:
        yield
    finally:
        _ACTIVE_AGENT_HARNESS.reset(token)


class HarnessedCompletionModel:
    """Counts a real completion only while an Agent request binds a harness.

    The adapter stays usable for non-Agent callers (for example an offline test),
    where no request budget exists and therefore no artificial count is made.
    """

    def __init__(self, delegate: CompletionModel, *, operation_name: str) -> None:
        if not operation_name.strip():
            raise ValueError("harnessed model operation_name must not be blank")
        self._delegate = delegate
        self._operation_name = operation_name

    @property
    def identity(self) -> str:
        return self._delegate.identity

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        def invoke_delegate() -> str:
            return self._delegate.complete(
                system_prompt=system_prompt,
                user_query=user_query,
            )

        active_harness = _ACTIVE_AGENT_HARNESS.get()
        if active_harness is None:
            return invoke_delegate()
        return active_harness.invoke_model(self._operation_name, invoke_delegate)

    def close(self) -> None:
        close = getattr(self._delegate, "close", None)
        if callable(close):
            close()


def _safe_failure_code(error: Exception) -> str:
    candidate = getattr(error, "failure_code", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    return "harness-operation-failed"
