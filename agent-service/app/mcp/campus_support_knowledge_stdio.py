"""Executable stdio entry point for the read-only campus knowledge MCP server."""

from __future__ import annotations

import argparse

from app.application.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeCitation,
)
from app.mcp.campus_support_knowledge_server import (
    build_campus_support_knowledge_mcp,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stdio-smoke-stub",
        action="store_true",
        help="Run a deterministic protocol-only test provider; never use in deployment.",
    )
    arguments = parser.parse_args()
    if arguments.stdio_smoke_stub:
        build_campus_support_knowledge_mcp(_SmokeProvider()).run(transport="stdio")
        return
    _run_production_server()


def _run_production_server() -> None:
    """Compose the same reviewed-corpus answer provider used by the API runtime."""
    # Imports are deliberately delayed: the protocol smoke must not load .env,
    # models, or the production corpus.
    from app.bootstrap import (
        build_current_support_knowledge_corpus,
        build_support_knowledge_answer_service,
        build_support_knowledge_text_embedder,
    )
    from app.config import load_settings
    from app.application.support_knowledge_dense_index_runtime import (
        SupportKnowledgeDenseIndexRuntime,
    )
    from app.infrastructure.json_file_dense_support_knowledge_index_store import (
        JsonFileDenseSupportKnowledgeIndexStore,
    )
    import httpx
    from app.bootstrap import _SUPPORT_KNOWLEDGE_DENSE_INDEX_PATH

    settings = load_settings()
    corpus = build_current_support_knowledge_corpus()
    dense_runtime: SupportKnowledgeDenseIndexRuntime | None = None
    provider = None
    try:
        if settings.dense_retrieval_enabled:
            dense_runtime = SupportKnowledgeDenseIndexRuntime(
                corpus,
                build_support_knowledge_text_embedder(
                    settings,
                    httpx.Client(timeout=settings.embedding_model_timeout_seconds),
                ),
                JsonFileDenseSupportKnowledgeIndexStore(
                    _SUPPORT_KNOWLEDGE_DENSE_INDEX_PATH
                ),
            )
            dense_runtime.prepare()
        provider = build_support_knowledge_answer_service(
            settings,
            corpus,
            dense_runtime,
        )
        build_campus_support_knowledge_mcp(provider).run(transport="stdio")
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()
        if dense_runtime is not None:
            dense_runtime.close()


class _SmokeProvider:
    """Protocol-test fixture; it has no corpus, model, or business dependency."""

    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        return SupportKnowledgeAnswer(
            status="answered",
            answer_text="MCP stdio protocol smoke answer.",
            citations=(
                SupportKnowledgeCitation(
                    article_id="mcp-stdio-smoke",
                    title="MCP protocol smoke fixture",
                    source_reference="test://mcp-stdio-smoke",
                ),
            ),
            model_called=False,
            retrieval_strategy="lexical",
        )


if __name__ == "__main__":
    main()
