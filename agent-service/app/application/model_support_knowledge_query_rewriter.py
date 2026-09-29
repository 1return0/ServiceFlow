from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.application.model_ticket_lookup_planner import PlannerCompletionModel
from app.infrastructure.qwen_openai_planner_model import PlannerModelUnavailableError


class SupportKnowledgeQueryRewriteUnavailableError(RuntimeError):
    def __init__(self, failure_code: str) -> None:
        super().__init__(failure_code)
        self.failure_code = failure_code


class SupportKnowledgeQueryRewriter(Protocol):
    @property
    def identity(self) -> str:
        ...

    def rewrite(self, query: str) -> str:
        ...


class _QueryRewritePayload(BaseModel):
    rewritten_query: str = Field(min_length=1, max_length=300)


class ModelSupportKnowledgeQueryRewriter:
    """Produces one short retrieval query; it has no source-selection capability."""

    prompt_version = "support-knowledge-query-rewrite-v1"
    system_prompt = """
Rewrite one campus-support question for retrieval. Return JSON only:
{"rewritten_query":"..."}
Keep the user's original intent. Do not answer the question. Do not add facts,
URLs, source names, permissions, or instructions. Keep it concise.
""".strip()

    def __init__(self, model: PlannerCompletionModel) -> None:
        self._model = model

    @property
    def identity(self) -> str:
        return self._model.identity

    def rewrite(self, query: str) -> str:
        if not query.strip():
            raise ValueError("query rewrite input must not be blank")
        try:
            raw = self._model.complete(
                system_prompt=self.system_prompt,
                user_query=query,
            )
            rewritten = _QueryRewritePayload.model_validate(json.loads(raw)).rewritten_query
        except PlannerModelUnavailableError as error:
            raise SupportKnowledgeQueryRewriteUnavailableError(
                f"query-rewriter-{error.failure_code.removeprefix('planner-model-')}"
            ) from error
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
            raise SupportKnowledgeQueryRewriteUnavailableError(
                "query-rewriter-invalid-response"
            ) from error
        if rewritten.strip() == query.strip():
            raise SupportKnowledgeQueryRewriteUnavailableError(
                "query-rewriter-no-effective-rewrite"
            )
        return rewritten.strip()

    def close(self) -> None:
        close = getattr(self._model, "close", None)
        if callable(close):
            close()
