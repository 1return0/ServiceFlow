from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


TriageDecision = Literal[
    "lookup_ticket",
    "get_notification_summary",
    "answer_support_knowledge",
    "handoff_to_human",
    "refuse",
]


class MultiAgentInvoker(Protocol):
    """The small executable boundary used by a golden evaluation."""

    def invoke(
        self,
        *,
        user_query: str,
        authorization: str | None = None,
    ) -> dict[str, object]: ...


@dataclass(frozen=True)
class MultiAgentEvaluationCase:
    case_id: str
    user_query: str
    expected_decision: TriageDecision | None
    expected_required_nodes: tuple[str, ...]
    authorization: str | None = None
    expected_failure_code: str | None = None

    def __post_init__(self) -> None:
        if self.expected_decision is None and self.expected_failure_code is None:
            raise ValueError("evaluation case requires a decision or failure code")
        if self.expected_decision is not None and self.expected_failure_code is not None:
            raise ValueError("evaluation case cannot expect both a decision and failure")


@dataclass(frozen=True)
class MultiAgentEvaluationCaseResult:
    case_id: str
    passed: bool
    expected_decision: TriageDecision | None
    actual_decision: str | None
    expected_required_nodes: tuple[str, ...]
    actual_nodes: tuple[str, ...]
    expected_failure_code: str | None
    actual_failure_code: str | None


@dataclass(frozen=True)
class MultiAgentEvaluationSummary:
    total_cases: int
    passed_cases: int
    decision_evaluated_cases: int
    decision_accuracy: float | None
    route_accuracy: float | None
    case_accuracy: float
    results: tuple[MultiAgentEvaluationCaseResult, ...]


class MultiAgentEvaluator:
    """Scores stable, executable facts; it intentionally ignores free-form reasons."""

    def evaluate(
        self,
        invoker: MultiAgentInvoker,
        cases: tuple[MultiAgentEvaluationCase, ...],
    ) -> MultiAgentEvaluationSummary:
        if not cases:
            raise ValueError("multi-agent evaluation requires at least one case")
        results = tuple(self._evaluate_case(invoker, case) for case in cases)
        decision_results = tuple(
            result for result in results if result.expected_decision is not None
        )
        decision_correct = sum(
            result.expected_decision == result.actual_decision
            for result in decision_results
        )
        route_correct = sum(
            _contains_nodes_in_order(result.actual_nodes, result.expected_required_nodes)
            for result in results
            if result.expected_failure_code is None
        )
        route_evaluated = sum(
            result.expected_failure_code is None for result in results
        )
        return MultiAgentEvaluationSummary(
            total_cases=len(results),
            passed_cases=sum(result.passed for result in results),
            decision_evaluated_cases=len(decision_results),
            decision_accuracy=(
                decision_correct / len(decision_results)
                if decision_results
                else None
            ),
            route_accuracy=(route_correct / route_evaluated if route_evaluated else None),
            case_accuracy=sum(result.passed for result in results) / len(results),
            results=results,
        )

    @staticmethod
    def _evaluate_case(
        invoker: MultiAgentInvoker,
        case: MultiAgentEvaluationCase,
    ) -> MultiAgentEvaluationCaseResult:
        try:
            result = invoker.invoke(
                user_query=case.user_query,
                authorization=case.authorization,
            )
        except Exception as error:
            actual_failure_code = getattr(error, "failure_code", None)
            if not isinstance(actual_failure_code, str) or not actual_failure_code:
                actual_failure_code = f"agent-exception:{type(error).__name__}"
            return MultiAgentEvaluationCaseResult(
                case_id=case.case_id,
                passed=actual_failure_code == case.expected_failure_code,
                expected_decision=case.expected_decision,
                actual_decision=None,
                expected_required_nodes=case.expected_required_nodes,
                actual_nodes=(),
                expected_failure_code=case.expected_failure_code,
                actual_failure_code=actual_failure_code,
            )

        actual_decision = result.get("decision")
        trace = result.get("trace")
        steps = getattr(trace, "steps", ())
        actual_nodes = tuple(
            node for step in steps if isinstance((node := getattr(step, "node", None)), str)
        )
        decision_correct = actual_decision == case.expected_decision
        route_correct = _contains_nodes_in_order(
            actual_nodes,
            case.expected_required_nodes,
        )
        return MultiAgentEvaluationCaseResult(
            case_id=case.case_id,
            passed=(
                case.expected_failure_code is None
                and decision_correct
                and route_correct
            ),
            expected_decision=case.expected_decision,
            actual_decision=actual_decision if isinstance(actual_decision, str) else None,
            expected_required_nodes=case.expected_required_nodes,
            actual_nodes=actual_nodes,
            expected_failure_code=case.expected_failure_code,
            actual_failure_code=None,
        )


def _contains_nodes_in_order(actual: tuple[str, ...], required: tuple[str, ...]) -> bool:
    position = 0
    for node in actual:
        if position < len(required) and node == required[position]:
            position += 1
    return position == len(required)
