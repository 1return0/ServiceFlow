from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.domain.ticket_lookup_plan import TicketLookupPlan, TicketLookupPlanner


@dataclass(frozen=True)
class PlannerEvaluationCase:
    """One fixed user request and its expected executable plan."""

    case_id: str
    user_query: str
    expected_decision: Literal["lookup_ticket", "refuse"]
    expected_ticket_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.expected_decision == "lookup_ticket" and self.expected_ticket_id is None:
            raise ValueError("lookup_ticket evaluation case requires expected_ticket_id")
        if self.expected_decision == "refuse" and self.expected_ticket_id is not None:
            raise ValueError("refuse evaluation case must not contain expected_ticket_id")


@dataclass(frozen=True)
class PlannerEvaluationCaseResult:
    case_id: str
    passed: bool
    expected_decision: str
    expected_ticket_id: UUID | None
    actual_plan: TicketLookupPlan | None
    failure_code: str | None = None


@dataclass(frozen=True)
class PlannerEvaluationSummary:
    total_cases: int
    passed_cases: int
    decision_accuracy: float
    ticket_id_evaluated_cases: int
    ticket_id_accuracy: float | None
    case_accuracy: float
    results: tuple[PlannerEvaluationCaseResult, ...]


class PlannerEvaluator:
    """Compares executable planning fields; free-form reasons are not scored."""

    def evaluate(
        self,
        planner: TicketLookupPlanner,
        cases: tuple[PlannerEvaluationCase, ...],
    ) -> PlannerEvaluationSummary:
        if not cases:
            raise ValueError("planner evaluation requires at least one case")

        results = tuple(
            self._evaluate_case(planner, case)
            for case in cases
        )
        total = len(results)
        decision_correct = sum(
            result.actual_plan is not None
            and result.expected_decision == result.actual_plan.decision
            for result in results
        )
        ticket_id_results = tuple(
            result
            for result in results
            if result.expected_decision == "lookup_ticket"
        )
        ticket_id_correct = sum(
            result.actual_plan is not None
            and result.expected_ticket_id == result.actual_plan.ticket_id
            for result in ticket_id_results
        )
        passed = sum(result.passed for result in results)
        return PlannerEvaluationSummary(
            total_cases=total,
            passed_cases=passed,
            decision_accuracy=decision_correct / total,
            ticket_id_evaluated_cases=len(ticket_id_results),
            ticket_id_accuracy=(
                ticket_id_correct / len(ticket_id_results)
                if ticket_id_results
                else None
            ),
            case_accuracy=passed / total,
            results=results,
        )

    @staticmethod
    def _evaluate_case(
        planner: TicketLookupPlanner,
        case: PlannerEvaluationCase,
    ) -> PlannerEvaluationCaseResult:
        try:
            actual_plan = planner.plan(user_query=case.user_query)
        except Exception as error:
            failure_code = getattr(error, "failure_code", None)
            return PlannerEvaluationCaseResult(
                case_id=case.case_id,
                passed=False,
                expected_decision=case.expected_decision,
                expected_ticket_id=case.expected_ticket_id,
                actual_plan=None,
                failure_code=(
                    failure_code
                    if isinstance(failure_code, str) and failure_code
                    else f"planner-exception:{type(error).__name__}"
                ),
            )
        passed = (
            actual_plan.decision == case.expected_decision
            and actual_plan.ticket_id == case.expected_ticket_id
        )
        return PlannerEvaluationCaseResult(
            case_id=case.case_id,
            passed=passed,
            expected_decision=case.expected_decision,
            expected_ticket_id=case.expected_ticket_id,
            actual_plan=actual_plan,
        )
