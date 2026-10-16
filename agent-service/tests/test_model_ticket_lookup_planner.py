import unittest

from app.application.agent.model_ticket_lookup_planner import (
    ModelTicketLookupPlanner,
    PlannerOutputError,
)


class FakePlannerModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_system_prompt: str | None = None
        self.last_user_query: str | None = None

    @property
    def identity(self) -> str:
        return "fake-planner-v1"

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_query = user_query
        return self.response


class ModelTicketLookupPlannerTest(unittest.TestCase):
    def test_decodes_a_valid_model_plan(self) -> None:
        model = FakePlannerModel(
            """
            {"decision":"call_tool","tool_name":"lookup_ticket","reason":"ticket ID found",
             "arguments":{"ticket_id":"009e3cce-8f4d-448d-a060-6ce2624eac77"}}
            """
        )
        planner = ModelTicketLookupPlanner(model)

        plan = planner.plan(
            user_query="请查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77"
        )

        self.assertEqual("lookup_ticket", plan.decision)
        self.assertEqual("fake-planner-v1", planner.identity)
        self.assertEqual("ticket-lookup-planner-prompt-v2", planner.prompt_version)
        self.assertIn("JSON only", model.last_system_prompt or "")

    def test_rejects_non_json_model_output(self) -> None:
        planner = ModelTicketLookupPlanner(
            FakePlannerModel("我认为应该查询该工单。")
        )

        with self.assertRaises(PlannerOutputError):
            planner.plan(user_query="请查询工单 009e3cce-8f4d-448d-a060-6ce2624eac77")

    def test_exposes_a_stable_failure_code_for_contract_violations(self) -> None:
        error = PlannerOutputError("test")

        self.assertEqual("planner-output-contract-violated", error.failure_code)

    def test_rejects_schema_valid_json_with_an_invalid_decision(self) -> None:
        planner = ModelTicketLookupPlanner(
            FakePlannerModel(
                '{"decision":"delete_ticket","reason":"bad","ticket_id":null}'
            )
        )

        with self.assertRaises(PlannerOutputError):
            planner.plan(user_query="删除工单")

    def test_rejects_a_refuse_plan_that_still_contains_a_ticket_id(self) -> None:
        planner = ModelTicketLookupPlanner(
            FakePlannerModel(
                '{"decision":"refuse","reason":"bad",'
                '"ticket_id":"009e3cce-8f4d-448d-a060-6ce2624eac77"}'
            )
        )

        with self.assertRaises(PlannerOutputError):
            planner.plan(user_query="不需要查询")


if __name__ == "__main__":
    unittest.main()
