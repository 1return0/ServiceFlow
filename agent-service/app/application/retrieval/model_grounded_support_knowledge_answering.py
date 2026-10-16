from __future__ import annotations

from typing import Protocol

from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeCitation,
    SupportKnowledgeSearcher,
    SupportKnowledgeRetrievalTraceStep,
    _search_with_metadata,
)


class SupportKnowledgeAnswerGenerator(Protocol):
    @property
    def identity(self) -> str:
        ...

    def generate(self, *, question: str, evidence_text: str) -> str:
        ...


class ModelGroundedSupportKnowledgeAnswerService:
    """Uses a model only after retrieval has selected one source article."""

    def __init__(
        self,
        searcher: SupportKnowledgeSearcher,
        generator: SupportKnowledgeAnswerGenerator,
    ) -> None:
        self._searcher = searcher
        self._generator = generator

    def answer(self, question: str, *, top_k: int = 3) -> SupportKnowledgeAnswer:
        search_result = _search_with_metadata(self._searcher, question, top_k=top_k)
        hits = search_result.hits
        metadata = search_result.metadata
        if not hits:
            return SupportKnowledgeAnswer(
                status="insufficient_evidence",
                answer_text="当前知识库没有检索到足够依据，请补充问题场景或转人工服务。",
                citations=(),
                retrieval_strategy=metadata.strategy,
                reranker_status=metadata.reranker_status,
                reranker_identity=metadata.reranker_identity,
                reranker_failure_code=metadata.reranker_failure_code,
                initial_evidence_count=metadata.initial_evidence_count,
                secondary_search_attempted=metadata.secondary_search_attempted,
                secondary_search_reason=metadata.secondary_search_reason,
                query_rewrite_attempted=metadata.query_rewrite_attempted,
                query_rewrite_status=metadata.query_rewrite_status,
                query_rewriter_identity=metadata.query_rewriter_identity,
                query_rewrite_failure_code=metadata.query_rewrite_failure_code,
                retrieval_trace=metadata.trace_steps + (
                    SupportKnowledgeRetrievalTraceStep(
                        "refusal_insufficient_evidence",
                        "refused",
                    ),
                ),
            )

        primary_hit = hits[0]
        primary_article = primary_hit.article
        generated_text = self._generator.generate(
            question=question,
            evidence_text=primary_hit.retrieved_text,
        )
        return SupportKnowledgeAnswer(
            status="answered",
            answer_text=generated_text,
            citations=(
                SupportKnowledgeCitation(
                    article_id=primary_article.article_id,
                    title=primary_article.title,
                    source_reference=primary_article.source_reference,
                    chunk_id=primary_hit.chunk_id,
                    fragment_location=primary_hit.fragment_location,
                ),
            ),
            model_called=True,
            model_identity=self._generator.identity,
            retrieval_strategy=metadata.strategy,
            reranker_status=metadata.reranker_status,
            reranker_identity=metadata.reranker_identity,
            reranker_failure_code=metadata.reranker_failure_code,
            initial_evidence_count=metadata.initial_evidence_count,
            secondary_search_attempted=metadata.secondary_search_attempted,
            secondary_search_reason=metadata.secondary_search_reason,
            query_rewrite_attempted=metadata.query_rewrite_attempted,
            query_rewrite_status=metadata.query_rewrite_status,
            query_rewriter_identity=metadata.query_rewriter_identity,
            query_rewrite_failure_code=metadata.query_rewrite_failure_code,
            retrieval_trace=metadata.trace_steps + (
                SupportKnowledgeRetrievalTraceStep(
                    "answer_model_generated",
                    "completed",
                ),
            ),
        )

    def close(self) -> None:
        close = getattr(self._generator, "close", None)
        if callable(close):
            close()
        searcher_close = getattr(self._searcher, "close", None)
        if callable(searcher_close):
            searcher_close()
