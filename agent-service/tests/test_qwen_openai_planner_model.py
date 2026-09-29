import json
import unittest

import httpx

from app.infrastructure.qwen_openai_planner_model import (
    PlannerModelUnavailableError,
    QwenOpenAICompatiblePlannerModel,
)


class QwenOpenAICompatiblePlannerModelTest(unittest.TestCase):
    def test_posts_a_deterministic_chat_completion_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("Bearer test-key", request.headers["Authorization"])
            self.assertEqual("/compatible-mode/v1/chat/completions", request.url.path)
            payload = json.loads(request.content)
            self.assertEqual("qwen-plus", payload["model"])
            self.assertEqual(0, payload["temperature"])
            self.assertEqual("system", payload["messages"][0]["role"])
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"decision":"refuse","reason":"x",'
                                    '"ticket_id":null}'
                                )
                            }
                        }
                    ]
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            model = QwenOpenAICompatiblePlannerModel(
                base_url="https://example.test/compatible-mode/v1",
                api_key="test-key",
                model="qwen-plus",
                http_client=http_client,
            )
            completion = model.complete(
                system_prompt="return JSON",
                user_query="查询工单",
            )

        self.assertIn('"decision":"refuse"', completion)
        self.assertEqual("qwen-openai-compatible:qwen-plus", model.identity)

    def test_normalizes_a_model_http_failure(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(401))
        ) as http_client:
            model = QwenOpenAICompatiblePlannerModel(
                base_url="https://example.test/compatible-mode/v1",
                api_key="test-key",
                model="qwen-plus",
                http_client=http_client,
            )
            with self.assertRaises(PlannerModelUnavailableError):
                model.complete(system_prompt="return JSON", user_query="查询工单")

    def test_exposes_a_stable_failure_code_for_authentication_errors(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(401))
        ) as http_client:
            model = QwenOpenAICompatiblePlannerModel(
                base_url="https://example.test/compatible-mode/v1",
                api_key="test-key",
                model="qwen-plus",
                http_client=http_client,
            )
            with self.assertRaises(PlannerModelUnavailableError) as raised:
                model.complete(system_prompt="return JSON", user_query="x")

        self.assertEqual(
            "planner-model-authentication-failed",
            raised.exception.failure_code,
        )

    def test_classifies_provider_quota_exhaustion_separately_from_authentication(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    403,
                    json={"error": {"code": "insufficient_quota"}},
                )
            )
        ) as http_client:
            model = QwenOpenAICompatiblePlannerModel(
                base_url="https://example.test/compatible-mode/v1",
                api_key="test-key",
                model="qwen-plus",
                http_client=http_client,
            )
            with self.assertRaises(PlannerModelUnavailableError) as raised:
                model.complete(system_prompt="return JSON", user_query="x")

        self.assertEqual(
            "planner-model-insufficient-quota",
            raised.exception.failure_code,
        )

    def test_classifies_a_timeout_separately_from_an_http_failure(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("simulated timeout", request=request)

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            model = QwenOpenAICompatiblePlannerModel(
                base_url="https://example.test/compatible-mode/v1",
                api_key="test-key",
                model="qwen-plus",
                http_client=http_client,
            )
            with self.assertRaises(PlannerModelUnavailableError) as raised:
                model.complete(system_prompt="return JSON", user_query="x")

        self.assertEqual("planner-model-timeout", raised.exception.failure_code)


if __name__ == "__main__":
    unittest.main()
