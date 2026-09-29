from __future__ import annotations

from unittest import TestCase

from app.application.knowledge_specialist_agent import (
    KnowledgeSpecialistAgent,
    TicketKnowledgeContext,
)
from app.application.support_knowledge_answering import SupportKnowledgeAnswer


class KnowledgeSpecialistAgentTest(TestCase):
    def test_delegates_a_normalized_question_to_its_single_tool(self) -> None:
        tool = _RecordingKnowledgeTool()
        agent = KnowledgeSpecialistAgent(tool)

        result = agent.answer(user_query="  校园网连不上怎么办？  ")

        self.assertEqual("answered", result.status)
        self.assertEqual(["校园网连不上怎么办？"], tool.questions)

    def test_rejects_a_blank_question_before_calling_the_tool(self) -> None:
        tool = _RecordingKnowledgeTool()
        agent = KnowledgeSpecialistAgent(tool)

        with self.assertRaisesRegex(ValueError, "non-blank"):
            agent.answer(user_query="  ")

        self.assertEqual([], tool.questions)

    def test_passes_only_category_and_status_as_ticket_retrieval_context(self) -> None:
        tool = _RecordingKnowledgeTool()
        agent = KnowledgeSpecialistAgent(tool)

        agent.answer(
            user_query="下一步怎么处理？",
            ticket_context=TicketKnowledgeContext(
                category="campus_network",
                status="RESOLVED",
            ),
        )

        self.assertEqual(
            [
                "下一步怎么处理？\n\n"
                "Ticket context for retrieval only: "
                "category=campus_network; status=RESOLVED"
            ],
            tool.questions,
        )


class _RecordingKnowledgeTool:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def execute(self, *, question: str, top_k: int = 3) -> SupportKnowledgeAnswer:
        self.questions.append(question)
        return SupportKnowledgeAnswer(
            status="answered",
            answer_text="请联系服务台。",
            citations=(),
        )
