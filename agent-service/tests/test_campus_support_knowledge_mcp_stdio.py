from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest import TestCase

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class CampusSupportKnowledgeMcpStdioTest(TestCase):
    def test_stdio_client_initializes_lists_and_calls_the_read_only_tool(self) -> None:
        async def smoke() -> tuple[list[str], object]:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "app.mcp.campus_support_knowledge_stdio", "--stdio-smoke-stub"],
                cwd=str(Path(__file__).resolve().parents[1]),
            )
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    result = await session.call_tool(
                        "search_campus_support_knowledge",
                        {"question": "How do I reset campus network access?", "top_k": 2},
                    )
                    return [tool.name for tool in tools.tools], result

        tool_names, result = asyncio.run(smoke())

        self.assertEqual(["search_campus_support_knowledge"], tool_names)
        self.assertFalse(result.isError)
        self.assertEqual("answered", result.structuredContent["status"])
        self.assertEqual(
            "mcp-stdio-smoke",
            result.structuredContent["citations"][0]["article_id"],
        )
