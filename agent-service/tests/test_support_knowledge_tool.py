from __future__ import annotations

from unittest import TestCase

from app.application.support_knowledge_answering import (
    SupportKnowledgeAnswer,
)
from app.application.support_knowledge_tool import SupportKnowledgeAnswerTool


class _RecordingKnowledgeAnswerProvider:
    def __init__(self) -> None:
        self.last_question: str | None = None
        self.last_top_k: int | None = None

    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        self.last_question = question
        self.last_top_k = top_k
        return SupportKnowledgeAnswer(
            status="insufficient_evidence",
            answer_text="no evidence",
            citations=(),
        )


class SupportKnowledgeAnswerToolTest(TestCase):
    def test_delegates_the_agent_tool_call_to_the_answer_provider(self) -> None:
        provider = _RecordingKnowledgeAnswerProvider()
        tool = SupportKnowledgeAnswerTool(provider)

        result = tool.execute(question="校园网连接失败怎么办？", top_k=2)

        self.assertEqual("answer_support_knowledge", tool.name)
        self.assertEqual("校园网连接失败怎么办？", provider.last_question)
        self.assertEqual(2, provider.last_top_k)
        self.assertEqual("insufficient_evidence", result.status)
