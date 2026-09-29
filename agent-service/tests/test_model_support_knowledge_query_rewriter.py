from __future__ import annotations

from unittest import TestCase

from app.application.model_support_knowledge_query_rewriter import (
    ModelSupportKnowledgeQueryRewriter,
    SupportKnowledgeQueryRewriteUnavailableError,
)
from app.infrastructure.qwen_openai_planner_model import PlannerModelUnavailableError


class ModelSupportKnowledgeQueryRewriterTest(TestCase):
    def test_requires_a_constrained_json_rewrite(self) -> None:
        rewriter = ModelSupportKnowledgeQueryRewriter(
            _Model('{"rewritten_query":"校园网认证失败处理"}')
        )

        self.assertEqual("校园网认证失败处理", rewriter.rewrite("校园网连不上"))
        self.assertEqual("test-model", rewriter.identity)

    def test_normalizes_provider_failure_without_leaking_provider_detail(self) -> None:
        rewriter = ModelSupportKnowledgeQueryRewriter(_UnavailableModel())

        with self.assertRaises(SupportKnowledgeQueryRewriteUnavailableError) as caught:
            rewriter.rewrite("校园网连不上")
        self.assertEqual("query-rewriter-timeout", caught.exception.failure_code)


class _Model:
    identity = "test-model"

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        return self._response


class _UnavailableModel:
    identity = "test-model"

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        raise PlannerModelUnavailableError("planner-model-timeout")
