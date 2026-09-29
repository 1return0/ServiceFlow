import unittest

from app.application.model_triage_planner import (
    ModelTriagePlanner,
    TriagePlannerOutputError,
)


class FakeCompletionModel:
    def __init__(self, response: str) -> None:
        self._response = response
        self.last_system_prompt: str | None = None
        self.last_user_query: str | None = None

    @property
    def identity(self) -> str:
        return "fake-triage-model-v1"

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_query = user_query
        return self._response


class ModelTriagePlannerTest(unittest.TestCase):
    def test_decodes_a_public_knowledge_decision(self) -> None:
        model = FakeCompletionModel(
            '{"decision":"answer_support_knowledge",'
            '"reason":"public network question","ticket_id":null}'
        )
        planner = ModelTriagePlanner(model)

        plan = planner.plan(user_query="校园网连接失败怎么办？")

        self.assertEqual("answer_support_knowledge", plan.decision)
        self.assertIsNone(plan.ticket_id)
        self.assertEqual("fake-triage-model-v1", planner.identity)
        self.assertEqual("campus-support-triage-prompt-v5", planner.prompt_version)
        self.assertIn("JSON only", model.last_system_prompt or "")
        self.assertIn("physical-safety", model.last_system_prompt or "")

    def test_decodes_a_handoff_decision(self) -> None:
        planner = ModelTriagePlanner(
            FakeCompletionModel(
                '{"decision":"handoff_to_human","reason":"smoke",'
                '"ticket_id":null,"handoff_reason":"physical_safety_risk"}'
            )
        )

        plan = planner.plan(user_query="教室投影仪冒烟怎么办？")

        self.assertEqual("handoff_to_human", plan.decision)
        self.assertEqual("physical_safety_risk", plan.handoff_reason)

    def test_decodes_a_ticket_decision(self) -> None:
        planner = ModelTriagePlanner(
            FakeCompletionModel(
                '{"decision":"lookup_ticket","reason":"UUID found",'
                '"ticket_id":"009e3cce-8f4d-448d-a060-6ce2624eac77"}'
            )
        )

        plan = planner.plan(user_query="查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77")

        self.assertEqual("lookup_ticket", plan.decision)
        self.assertIsNotNone(plan.ticket_id)

    def test_rejects_a_schema_valid_but_business_invalid_plan(self) -> None:
        planner = ModelTriagePlanner(
            FakeCompletionModel(
                '{"decision":"answer_support_knowledge","reason":"bad",'
                '"ticket_id":"009e3cce-8f4d-448d-a060-6ce2624eac77"}'
            )
        )

        with self.assertRaises(TriagePlannerOutputError):
            planner.plan(user_query="校园网怎么办？")

    def test_rejects_non_json_model_output(self) -> None:
        planner = ModelTriagePlanner(FakeCompletionModel("请走知识问答能力"))

        with self.assertRaises(TriagePlannerOutputError):
            planner.plan(user_query="校园网怎么办？")


if __name__ == "__main__":
    unittest.main()
