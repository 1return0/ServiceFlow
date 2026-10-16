from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeAnswerProvider,
)


class SupportKnowledgeArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000,
                          description="Current campus-support question, retaining the user's intent and constraints.")


class SupportKnowledgeAnswerTool:
    """Agent tool boundary for answering campus support questions from evidence."""

    name = "answer_support_knowledge"
    description = "Answer public campus IT or teaching-service questions from reviewed evidence with citations. Retrieval depth is runtime-controlled."
    arguments_model = SupportKnowledgeArguments
    routing_decision = "answer_support_knowledge"

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return self.arguments_model.model_json_schema()

    def invoke(self, raw_arguments: dict[str, Any]) -> SupportKnowledgeAnswer:
        arguments = self.arguments_model.model_validate(raw_arguments)
        return self.execute(question=arguments.question)

    def __init__(self, answer_provider: SupportKnowledgeAnswerProvider) -> None:
        self._answer_provider = answer_provider

    def execute(self, *, question: str, top_k: int = 3) -> SupportKnowledgeAnswer:
        arguments = self.arguments_model(question=question)
        return self._answer_provider.answer(arguments.question, top_k=top_k)
