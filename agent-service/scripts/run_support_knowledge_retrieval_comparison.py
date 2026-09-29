from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path

import httpx

from app.application.hybrid_support_knowledge_chunk_retriever import (
    HybridSupportKnowledgeChunkRetriever,
)
from app.application.retrieval_comparison_evaluation import (
    run_retrieval_comparison_evaluation,
    write_retrieval_comparison_report,
)
from app.application.reranking_support_knowledge_chunk_retriever import (
    RerankingSupportKnowledgeChunkRetriever,
)
from app.application.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever,
)
from app.application.support_knowledge_dense_index_runtime import (
    SupportKnowledgeDenseIndexRuntime,
)
from app.bootstrap import (
    build_current_support_knowledge_corpus,
    build_support_knowledge_reranker,
    build_support_knowledge_text_embedder,
)
from app.config import load_settings
from app.infrastructure.json_file_dense_support_knowledge_index_store import (
    JsonFileDenseSupportKnowledgeIndexStore,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare BM25, Dense, Hybrid, and Hybrid+Rerank on one frozen dataset."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/retrieval-evaluation/support-knowledge-retrieval-v1.json"),
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    settings = load_settings()
    if not settings.dense_retrieval_enabled or not settings.reranker_enabled:
        raise ValueError(
            "set SERVICEFLOW_DENSE_RETRIEVAL_ENABLED and SERVICEFLOW_RERANKER_ENABLED to true"
        )
    corpus = build_current_support_knowledge_corpus()
    index_path = Path("data/support-knowledge/dense-index.json")
    embedder = build_support_knowledge_text_embedder(
        settings,
        httpx.Client(timeout=settings.embedding_model_timeout_seconds),
    )
    runtime = SupportKnowledgeDenseIndexRuntime(
        corpus,
        embedder,
        JsonFileDenseSupportKnowledgeIndexStore(index_path),
    )
    reranker = build_support_knowledge_reranker(settings)
    try:
        runtime.prepare()
        _revision, _articles, chunks = corpus.retrieval_snapshot()
        bm25 = LexicalSupportKnowledgeChunkRetriever(chunks)
        hybrid = HybridSupportKnowledgeChunkRetriever(
            bm25,
            runtime,
            candidate_k=settings.hybrid_candidate_k,
            rank_constant=settings.hybrid_rank_constant,
        )
        report = run_retrieval_comparison_evaluation(
            corpus=corpus,
            retrievers=OrderedDict((
                ("bm25", bm25),
                ("dense", runtime),
                ("hybrid", hybrid),
                (
                    "hybrid_rerank",
                    RerankingSupportKnowledgeChunkRetriever(
                        hybrid,
                        reranker,
                        candidate_k=settings.reranker_candidate_k,
                    ),
                ),
            )),
            dataset_path=arguments.dataset,
            top_k=arguments.top_k,
        )
        write_retrieval_comparison_report(report, arguments.output)
        print(arguments.output)
    finally:
        runtime.close()
        reranker.close()


if __name__ == "__main__":
    main()
