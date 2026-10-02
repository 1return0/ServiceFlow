from __future__ import annotations

from unittest import TestCase

from app.application.agent_harness import (
    AgentHarness,
    AgentHarnessLimitExceededError,
    AgentHarnessLimits,
    HarnessedCompletionModel,
    bind_agent_harness,
)


class AgentHarnessTest(TestCase):
    def test_records_safe_model_and_tool_counts_without_payloads(self) -> None:
        clock = _Clock(0.0, 0.0, 0.2, 0.2, 0.5, 0.5, 0.8, 0.8)
        harness = AgentHarness(time_source=clock)

        self.assertEqual("plan", harness.invoke_model("triage_planner", lambda: "plan"))
        self.assertEqual(
            {"private_payload": "answer"},
            harness.invoke_tool(
                "knowledge_answer",
                lambda: {"private_payload": "answer"},
            ),
        )

        snapshot = harness.snapshot()
        self.assertEqual(1, snapshot.model_call_count)
        self.assertEqual(1, snapshot.tool_call_count)
        self.assertEqual(
            ("triage_planner", "knowledge_answer"),
            tuple(step.operation_name for step in snapshot.steps),
        )
        self.assertNotIn("private_payload", repr(snapshot.steps[1]))

    def test_rejects_second_model_call_before_executing_it(self) -> None:
        harness = AgentHarness(AgentHarnessLimits(max_model_calls=1))
        harness.invoke_model("triage_planner", lambda: None)
        executed = False

        def forbidden() -> None:
            nonlocal executed
            executed = True

        with self.assertRaisesRegex(
            AgentHarnessLimitExceededError,
            "harness-model-call-limit-reached",
        ):
            harness.invoke_model("query_rewriter", forbidden)

        self.assertFalse(executed)
        self.assertEqual("rejected", harness.snapshot().steps[-1].status)

    def test_keeps_only_stable_failure_code_not_exception_detail(self) -> None:
        harness = AgentHarness()

        with self.assertRaises(RuntimeError):
            harness.invoke_tool(
                "knowledge_answer",
                lambda: (_ for _ in ()).throw(
                    RuntimeError("private vendor response and token")
                ),
            )

        step = harness.snapshot().steps[-1]
        self.assertEqual("failed", step.status)
        self.assertEqual("harness-operation-failed", step.failure_code)
        self.assertNotIn("private vendor", repr(step))

    def test_counts_only_a_real_model_call_inside_the_bound_request(self) -> None:
        delegate = _CompletionModel()
        model = HarnessedCompletionModel(
            delegate,
            operation_name="triage_planner_model",
        )
        harness = AgentHarness()

        self.assertEqual("{}", model.complete(system_prompt="system", user_query="one"))
        with bind_agent_harness(harness):
            self.assertEqual("{}", model.complete(system_prompt="system", user_query="two"))

        self.assertEqual(2, delegate.call_count)
        snapshot = harness.snapshot()
        self.assertEqual(1, snapshot.model_call_count)
        self.assertEqual("triage_planner_model", snapshot.steps[0].operation_name)


class _Clock:
    def __init__(self, *values: float) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


class _CompletionModel:
    identity = "test:model-v1"

    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        self.call_count += 1
        return "{}"
