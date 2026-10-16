from __future__ import annotations

from dataclasses import replace

from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeSearchResult,
    SupportKnowledgeSearcher,
    _search_with_metadata,
    SupportKnowledgeRetrievalTraceStep,
)
from app.application.retrieval.model_support_knowledge_query_rewriter import (
    SupportKnowledgeQueryRewriter,
    SupportKnowledgeQueryRewriteUnavailableError,
)


class ControlledSecondarySupportKnowledgeSearcher:
    """Performs at most one wider retry, only when the first evidence set is too small."""

    def __init__(
        self,
        searcher: SupportKnowledgeSearcher,
        *,
        minimum_evidence_count: int = 2,
        secondary_top_k: int = 6,
        query_rewriter: SupportKnowledgeQueryRewriter | None = None,
    ) -> None:
        if minimum_evidence_count <= 0:
            raise ValueError("minimum_evidence_count must be positive")
        if secondary_top_k <= 0:
            raise ValueError("secondary_top_k must be positive")
        self._searcher = searcher
        self._minimum_evidence_count = minimum_evidence_count
        self._secondary_top_k = secondary_top_k
        self._query_rewriter = query_rewriter

    def search(self, query: str, *, top_k: int = 3):
        return self.search_with_metadata(query, top_k=top_k).hits

    def search_with_metadata(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> SupportKnowledgeSearchResult:
        initial = _search_with_metadata(self._searcher, query, top_k=top_k)
        required_evidence_count = min(self._minimum_evidence_count, top_k)
        if len(initial.hits) >= required_evidence_count:
            return SupportKnowledgeSearchResult(
                hits=initial.hits,
                metadata=replace(
                    initial.metadata,
                    initial_evidence_count=len(initial.hits),
                    trace_steps=_prefixed_trace("initial", initial.metadata.trace_steps) + (
                        SupportKnowledgeRetrievalTraceStep(
                            "initial_evidence_gate",
                            "completed",
                        ),
                    ),
                ),
            )

        secondary_query = query
        query_rewrite_attempted = False
        query_rewrite_status = "not_requested"
        query_rewriter_identity: str | None = None
        query_rewrite_failure_code: str | None = None
        if self._query_rewriter is not None:
            query_rewrite_attempted = True
            query_rewriter_identity = self._query_rewriter.identity
            try:
                secondary_query = self._query_rewriter.rewrite(query)
                query_rewrite_status = "applied"
            except SupportKnowledgeQueryRewriteUnavailableError as error:
                # The fallback retains the original source scope and query. It does
                # not claim that a rewrite occurred.
                query_rewrite_status = "degraded"
                query_rewrite_failure_code = error.failure_code

        # Exactly one bounded second search. The rewriter receives only the user
        # query; it cannot choose extra source repositories or permissions.
        secondary = _search_with_metadata(
            self._searcher,
            secondary_query,
            top_k=max(top_k, self._secondary_top_k),
        )
        hits_by_chunk_id = {hit.chunk_id: hit for hit in initial.hits}
        merged = list(initial.hits)
        for hit in secondary.hits:
            if hit.chunk_id not in hits_by_chunk_id:
                hits_by_chunk_id[hit.chunk_id] = hit
                merged.append(hit)
        return SupportKnowledgeSearchResult(
            hits=tuple(merged[:top_k]),
            metadata=replace(
                secondary.metadata,
                initial_evidence_count=len(initial.hits),
                secondary_search_attempted=True,
                secondary_search_reason="insufficient-initial-evidence",
                query_rewrite_attempted=query_rewrite_attempted,
                query_rewrite_status=query_rewrite_status,
                query_rewriter_identity=query_rewriter_identity,
                query_rewrite_failure_code=query_rewrite_failure_code,
                trace_steps=_prefixed_trace("initial", initial.metadata.trace_steps)
                + (SupportKnowledgeRetrievalTraceStep("initial_evidence_gate", "completed"),)
                + (
                    (
                        SupportKnowledgeRetrievalTraceStep(
                            "query_rewrite",
                            "applied" if query_rewrite_status == "applied" else "degraded",
                        ),
                    )
                    if query_rewrite_attempted
                    else ()
                )
                + _prefixed_trace("secondary", secondary.metadata.trace_steps)
                + (SupportKnowledgeRetrievalTraceStep("secondary_retrieval", "completed"),),
            ),
        )

    def close(self) -> None:
        close = getattr(self._searcher, "close", None)
        if callable(close):
            close()
        rewriter_close = getattr(self._query_rewriter, "close", None)
        if callable(rewriter_close):
            rewriter_close()


def _prefixed_trace(prefix: str, steps):
    return tuple(
        SupportKnowledgeRetrievalTraceStep(f"{prefix}_{step.stage}", step.status)
        for step in steps
    )
