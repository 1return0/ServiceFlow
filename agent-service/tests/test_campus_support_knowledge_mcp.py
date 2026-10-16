from __future__ import annotations

import asyncio
import time
from unittest import TestCase

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeCitation,
)
from app.mcp.campus_support_knowledge_server import (
    CampusSupportKnowledgeQuery,
    build_campus_support_knowledge_mcp,
)


class CampusSupportKnowledgeMcpTest(TestCase):
    def test_exposes_only_one_read_only_knowledge_tool(self) -> None:
        provider = _RecordingProvider()
        server = build_campus_support_knowledge_mcp(provider)

        tools = asyncio.run(server.list_tools())

        self.assertEqual(["search_campus_support_knowledge"], [tool.name for tool in tools])
        self.assertIn("read-only", tools[0].description)
        self.assertNotIn("ticket", tools[0].inputSchema["properties"])

    def test_tool_validates_input_and_returns_safe_auditable_output(self) -> None:
        provider = _RecordingProvider()
        server = build_campus_support_knowledge_mcp(provider)

        _, structured_result = asyncio.run(
            server.call_tool(
                "search_campus_support_knowledge",
                {"question": "How do I reset campus network access?", "top_k": 2},
            )
        )

        self.assertEqual(
            ("How do I reset campus network access?", 2), provider.calls[0]
        )
        self.assertEqual("answered", structured_result["status"])
        self.assertEqual(
            "reviewed-network-guide",
            structured_result["citations"][0]["article_id"],
        )
        self.assertNotIn("retrieval_trace", structured_result)
        self.assertNotIn("authorization", structured_result)

    def test_public_query_contract_rejects_blank_question_and_large_top_k(self) -> None:
        with self.assertRaises(ValidationError):
            CampusSupportKnowledgeQuery.model_validate({"question": "", "top_k": 3})
        with self.assertRaises(ValidationError):
            CampusSupportKnowledgeQuery.model_validate({"question": "network", "top_k": 6})

    def test_maps_provider_timeout_to_a_stable_mcp_error(self) -> None:
        server = build_campus_support_knowledge_mcp(
            _SlowProvider(),
            timeout_seconds=0.01,
        )

        with self.assertRaisesRegex(ToolError, "campus-support-knowledge-timeout"):
            asyncio.run(
                server.call_tool(
                    "search_campus_support_knowledge",
                    {"question": "How do I reset campus network access?"},
                )
            )

    def test_maps_provider_exception_without_leaking_its_message(self) -> None:
        server = build_campus_support_knowledge_mcp(_FailingProvider())

        with self.assertRaises(ToolError) as caught:
            asyncio.run(
                server.call_tool(
                    "search_campus_support_knowledge",
                    {"question": "How do I reset campus network access?"},
                )
            )

        self.assertIn("campus-support-knowledge-unavailable", str(caught.exception))
        self.assertNotIn("private vendor response", str(caught.exception))


class _RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        self.calls.append((question, top_k))
        return SupportKnowledgeAnswer(
            status="answered",
            answer_text="Reset the campus network password through the portal.",
            citations=(
                SupportKnowledgeCitation(
                    article_id="reviewed-network-guide",
                    title="Campus network access",
                    source_reference="review://network-guide-v1",
                    chunk_id="chunk-network-01",
                    fragment_location="paragraph:2",
                ),
            ),
            model_called=False,
            retrieval_strategy="hybrid",
            secondary_search_attempted=True,
            query_rewrite_status="degraded",
        )


class _SlowProvider:
    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        time.sleep(0.05)
        raise AssertionError("the client should have timed out first")


class _FailingProvider:
    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        raise RuntimeError("private vendor response: internal endpoint")
