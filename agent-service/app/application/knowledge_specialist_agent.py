from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.application.support_knowledge_answering import SupportKnowledgeAnswer
from app.application.support_knowledge_tool import SupportKnowledgeAnswerTool


@dataclass(frozen=True)
class TicketKnowledgeContext:
    """The minimal non-sensitive ticket facts allowed to guide public RAG."""

    category: str
    status: str


class KnowledgeSpecialist(Protocol):
    """A bounded worker that answers only public campus-service knowledge."""

    @property
    def identity(self) -> str:
        ...

    def answer(
        self,
        *,
        user_query: str,
        ticket_context: TicketKnowledgeContext | None = None,
    ) -> SupportKnowledgeAnswer:
        ...


class KnowledgeSpecialistAgent:
    """Specialised Agent worker that owns the knowledge-answer tool boundary."""

    identity = "knowledge-specialist-agent-v1"

    def __init__(self, knowledge_answer_tool: SupportKnowledgeAnswerTool) -> None:
        self._knowledge_answer_tool = knowledge_answer_tool

    def answer(
        self,
        *,
        user_query: str,
        ticket_context: TicketKnowledgeContext | None = None,
    ) -> SupportKnowledgeAnswer:
        normalized_query = user_query.strip()
        if not normalized_query:
            raise ValueError("knowledge specialist requires a non-blank user_query")
        question = normalized_query
        if ticket_context is not None:
            question = (
                f"{normalized_query}\n\n"
                "Ticket context for retrieval only: "
                f"category={ticket_context.category}; "
                f"status={ticket_context.status}"
            )
        return self._knowledge_answer_tool.execute(question=question)
