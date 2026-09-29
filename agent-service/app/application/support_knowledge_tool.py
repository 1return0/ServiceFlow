from __future__ import annotations

from app.application.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeAnswerProvider,
)


class SupportKnowledgeAnswerTool:
    """Agent tool boundary for answering campus support questions from evidence."""

    name = "answer_support_knowledge"

    def __init__(self, answer_provider: SupportKnowledgeAnswerProvider) -> None:
        self._answer_provider = answer_provider

    def execute(self, *, question: str, top_k: int = 3) -> SupportKnowledgeAnswer:
        return self._answer_provider.answer(question, top_k=top_k)
