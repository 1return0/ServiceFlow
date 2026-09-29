from __future__ import annotations

from app.application.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever,
)
from app.application.support_knowledge_retrieval import SupportKnowledgeSearchHit
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus


class RefreshableSupportKnowledgeChunkRetriever:
    """Indexes current chunks and enriches each hit with its parent article."""

    def __init__(self, corpus: CurrentSupportKnowledgeCorpus) -> None:
        self._corpus = corpus
        self._indexed_revision = -1
        self._delegate: LexicalSupportKnowledgeChunkRetriever | None = None
        self._articles_by_id = {}

    def search(self, query: str, *, top_k: int = 3):
        revision, articles, chunks = self._corpus.retrieval_snapshot()
        if self._delegate is None or revision != self._indexed_revision:
            self._delegate = LexicalSupportKnowledgeChunkRetriever(chunks)
            self._articles_by_id = {
                article.article_id: article for article in articles
            }
            self._indexed_revision = revision
        chunk_hits = self._delegate.search(query, top_k=top_k)
        return tuple(
            SupportKnowledgeSearchHit(
                article=self._articles_by_id[hit.chunk.article_id],
                score=hit.score,
                evidence_text=hit.chunk.text,
                chunk_id=hit.chunk.chunk_id,
                fragment_location=hit.chunk.fragment_location,
            )
            for hit in chunk_hits
        )
