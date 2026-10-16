from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from app.application.retrieval.model_grounded_support_knowledge_answering import (
    ModelGroundedSupportKnowledgeAnswerService,
)
from app.application.retrieval.support_knowledge_retrieval import (
    LexicalSupportKnowledgeRetriever,
)
from app.infrastructure.persistence.json_support_knowledge_catalog import (
    JsonSupportKnowledgeCatalog,
)


class _FakeKnowledgeAnswerGenerator:
    identity = "fake-qwen:knowledge-prompt-v1"

    def __init__(self) -> None:
        self.called = False

    def generate(self, *, question: str, evidence_text: str) -> str:
        self.called = True
        return f"根据资料：{evidence_text}"


class ModelGroundedSupportKnowledgeAnswerServiceTest(TestCase):
    def setUp(self) -> None:
        retriever = LexicalSupportKnowledgeRetriever(
            JsonSupportKnowledgeCatalog(
                Path("data/support-knowledge/demo-campus-support-v1.json")
            )
        )
        self.generator = _FakeKnowledgeAnswerGenerator()
        self.service = ModelGroundedSupportKnowledgeAnswerService(
            retriever,
            self.generator,
        )

    def test_calls_the_generator_only_after_retrieval_and_preserves_source(self) -> None:
        answer = self.service.answer("教学系统打不开，课程无法访问怎么办？")

        self.assertTrue(self.generator.called)
        self.assertTrue(answer.model_called)
        self.assertEqual("fake-qwen:knowledge-prompt-v1", answer.model_identity)
        self.assertEqual("course-system-v1", answer.citations[0].article_id)

    def test_does_not_call_the_generator_when_evidence_is_missing(self) -> None:
        answer = self.service.answer("食堂今天有什么菜？")

        self.assertFalse(self.generator.called)
        self.assertFalse(answer.model_called)
        self.assertEqual("insufficient_evidence", answer.status)
