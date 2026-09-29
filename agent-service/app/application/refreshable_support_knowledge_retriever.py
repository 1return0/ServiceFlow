from __future__ import annotations

from app.application.support_knowledge_retrieval import (
    LexicalSupportKnowledgeRetriever,
    SupportKnowledgeSearchHit,
)
from app.domain.support_knowledge import (
    CurrentSupportKnowledgeCorpus,
    SupportKnowledgeArticle,
)


class _FixedSupportKnowledgeCatalog:
    def __init__(self, articles: tuple[SupportKnowledgeArticle, ...]) -> None:
        self._articles = articles

    def list_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        return self._articles


class RefreshableLexicalSupportKnowledgeRetriever:
    """Rebuilds its small BM25 index only when the current corpus changes."""

    def __init__(self, corpus: CurrentSupportKnowledgeCorpus) -> None:
        self._corpus = corpus
        self._indexed_revision = -1
        self._delegate: LexicalSupportKnowledgeRetriever | None = None

    @property
    def indexed_revision(self) -> int:
        return self._indexed_revision

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeSearchHit, ...]:
        revision, articles = self._corpus.snapshot()
        if self._delegate is None or revision != self._indexed_revision:
            self._delegate = LexicalSupportKnowledgeRetriever(
                _FixedSupportKnowledgeCatalog(articles)
            )
            self._indexed_revision = revision
        return self._delegate.search(query, top_k=top_k)
