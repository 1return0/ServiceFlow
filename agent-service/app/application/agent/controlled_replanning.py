"""Fixed, auditable limits for a single read-only Agent replanning attempt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ReplanDecision = Literal["continue", "replan_once", "stop"]


@dataclass(frozen=True, slots=True)
class ReplanAssessment:
    decision: ReplanDecision
    reason_code: str


class ControlledReplanPolicy:
    _RECOVERABLE_READ_FAILURES = frozenset(
        {"insufficient_evidence", "no_matches"}
    )

    def assess(
        self,
        *,
        result_code: str,
        replan_count: int,
        operation_kind: Literal["read", "write"],
    ) -> ReplanAssessment:
        if replan_count < 0:
            raise ValueError("replan_count must not be negative")
        if operation_kind == "write":
            return ReplanAssessment("stop", "write-operation-never-replanned")
        if replan_count >= 1:
            return ReplanAssessment("stop", "replan-limit-reached")
        if result_code in self._RECOVERABLE_READ_FAILURES:
            return ReplanAssessment("replan_once", result_code)
        return ReplanAssessment("stop", "non-recoverable-result")
