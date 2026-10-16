"""Read-only MCP surface for reviewed campus-support knowledge."""

from __future__ import annotations

import asyncio
from typing import Literal

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeAnswerProvider,
)


class CampusSupportKnowledgeQuery(BaseModel):
    """The entire public input contract for the MCP tool."""

    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=5)


class CampusSupportKnowledgeCitationResult(BaseModel):
    article_id: str
    title: str
    source_reference: str
    chunk_id: str | None = None
    fragment_location: str | None = None


class CampusSupportKnowledgeResult(BaseModel):
    """Safe result schema; it excludes internal trace and credential fields."""

    status: Literal["answered", "insufficient_evidence"]
    answer_text: str
    citations: list[CampusSupportKnowledgeCitationResult]
    model_called: bool
    retrieval_strategy: Literal[
        "lexical",
        "hybrid",
        "hybrid_reranked",
        "hybrid_rerank_degraded",
    ]
    secondary_search_attempted: bool
    query_rewrite_status: Literal["not_requested", "applied", "degraded"]


def build_campus_support_knowledge_mcp(
    answer_provider: SupportKnowledgeAnswerProvider,
    *,
    timeout_seconds: float = 10.0,
) -> FastMCP:
    """Build one read-only MCP server without giving it ticket capabilities."""
    if timeout_seconds <= 0:
        raise ValueError("MCP knowledge timeout must be positive")

    server = FastMCP(
        "serviceflow-campus-support-knowledge",
        instructions=(
            "Search reviewed campus-support knowledge only. This server cannot "
            "read or modify tickets, notifications, accounts, or human handoffs."
        ),
    )

    @server.tool(
        name="search_campus_support_knowledge",
        description=(
            "Answer a campus-support question only from the reviewed knowledge "
            "corpus. This is read-only and returns citations."
        ),
    )
    async def search_campus_support_knowledge(
        question: str,
        top_k: int = 3,
    ) -> dict[str, object]:
        query = CampusSupportKnowledgeQuery.model_validate(
            {"question": question, "top_k": top_k}
        )
        answer = await _answer_with_timeout(
            answer_provider,
            question=query.question,
            top_k=query.top_k,
            timeout_seconds=timeout_seconds,
        )
        return _result_from_answer(answer).model_dump(mode="json")

    return server


async def _answer_with_timeout(
    answer_provider: SupportKnowledgeAnswerProvider,
    *,
    question: str,
    top_k: int,
    timeout_seconds: float,
) -> SupportKnowledgeAnswer:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(answer_provider.answer, question, top_k=top_k),
            timeout=timeout_seconds,
        )
    except TimeoutError as error:
        raise ToolError("campus-support-knowledge-timeout") from error
    except ToolError:
        raise
    except Exception as error:
        # Do not expose model/vendor/network exception text through MCP.
        raise ToolError("campus-support-knowledge-unavailable") from error


def _result_from_answer(
    answer: SupportKnowledgeAnswer,
) -> CampusSupportKnowledgeResult:
    return CampusSupportKnowledgeResult(
        status=answer.status,
        answer_text=answer.answer_text,
        citations=[
            CampusSupportKnowledgeCitationResult(
                article_id=citation.article_id,
                title=citation.title,
                source_reference=citation.source_reference,
                chunk_id=citation.chunk_id,
                fragment_location=citation.fragment_location,
            )
            for citation in answer.citations
        ],
        model_called=answer.model_called,
        retrieval_strategy=answer.retrieval_strategy,
        secondary_search_attempted=answer.secondary_search_attempted,
        query_rewrite_status=answer.query_rewrite_status,
    )
