from __future__ import annotations

import json
from unittest import TestCase

import httpx

from app.infrastructure.qwen_openai_compatible_support_knowledge_reranker import (
    QwenOpenAICompatibleSupportKnowledgeReranker,
    SupportKnowledgeRerankerUnavailableError,
)


class QwenOpenAICompatibleSupportKnowledgeRerankerTest(TestCase):
    def test_sends_only_candidates_and_restores_provider_indices(self) -> None:
        observed: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            observed["url"] = str(request.url)
            observed["body"] = json.loads(request.content)
            return httpx.Response(200, json={"results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.1},
            ]})

        reranker = QwenOpenAICompatibleSupportKnowledgeReranker(
            base_url="https://model.example/v1",
            api_key="test-key",
            model="qwen3-rerank",
            revision="r1",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        results = reranker.rerank("校园网", ("网络认证", "图书馆借阅"))

        self.assertEqual("https://model.example/v1/reranks", observed["url"])
        self.assertEqual(
            ["网络认证", "图书馆借阅"],
            observed["body"]["documents"],
        )
        self.assertEqual((1, 0), tuple(result.candidate_index for result in results))

    def test_normalizes_authentication_failure(self) -> None:
        reranker = QwenOpenAICompatibleSupportKnowledgeReranker(
            base_url="https://model.example/v1",
            api_key="test-key",
            model="qwen3-rerank",
            revision="r1",
            http_client=httpx.Client(
                transport=httpx.MockTransport(lambda request: httpx.Response(403))
            ),
        )

        with self.assertRaises(SupportKnowledgeRerankerUnavailableError) as caught:
            reranker.rerank("校园网", ("网络认证",))
        self.assertEqual("reranker-model-authentication-failed", caught.exception.failure_code)
