from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from app.domain.support_knowledge import (
    SupportKnowledgeArticle,
    SupportKnowledgeCatalog,
)


_LATIN_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SupportKnowledgeSearchHit:
    article: SupportKnowledgeArticle
    score: float
    evidence_text: str | None = None
    chunk_id: str | None = None
    fragment_location: str | None = None

    @property
    def retrieved_text(self) -> str:
        return self.evidence_text or self.article.content


class LexicalSupportKnowledgeRetriever:
    """Small BM25 baseline for the local campus-support demonstration corpus."""

    def __init__(self, catalog: SupportKnowledgeCatalog) -> None:
        self._articles = catalog.list_articles()
        self._document_tokens = tuple(
            _tokenize(f"{article.title} {article.content}")
            for article in self._articles
        )
        self._document_frequencies = Counter(
            token
            for tokens in self._document_tokens
            for token in set(tokens)
        )
        self._average_document_length = (
            sum(len(tokens) for tokens in self._document_tokens)
            / len(self._document_tokens)
            if self._document_tokens
            else 0.0
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> tuple[SupportKnowledgeSearchHit, ...]:
        if not query.strip():
            raise ValueError("support knowledge search query must not be blank")
        if top_k <= 0:
            raise ValueError("support knowledge search top_k must be positive")

        query_tokens = _tokenize(query)
        scored_hits = tuple(
            SupportKnowledgeSearchHit(
                article=article,
                score=self._score(query_tokens, document_tokens),
            )
            for article, document_tokens in zip(
                self._articles,
                self._document_tokens,
                strict=True,
            )
        )
        return tuple(
            hit
            for hit in sorted(
                scored_hits,
                key=lambda hit: (-hit.score, hit.article.article_id),
            )
            if hit.score > 0
        )[:top_k]

    def _score(
        self,
        query_tokens: tuple[str, ...],
        document_tokens: tuple[str, ...],
    ) -> float:
        if not query_tokens or not document_tokens or not self._articles:
            return 0.0

        term_frequencies = Counter(document_tokens)
        document_length = len(document_tokens)
        score = 0.0
        for token in set(query_tokens):
            document_frequency = self._document_frequencies.get(token, 0)
            if document_frequency == 0:
                continue
            inverse_document_frequency = math.log(
                1
                + (len(self._articles) - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            term_frequency = term_frequencies.get(token, 0)
            normalized_term_frequency = term_frequency * (1.2 + 1) / (
                term_frequency
                + 1.2
                * (1 - 0.75 + 0.75 * document_length / self._average_document_length)
            )
            score += inverse_document_frequency * normalized_term_frequency
        return score


def _tokenize(text: str) -> tuple[str, ...]:
    normalized = text.casefold()
    latin_tokens = _LATIN_TOKEN_PATTERN.findall(normalized)
    chinese_characters = tuple(
        character
        for character in normalized
        if "\u4e00" <= character <= "\u9fff"
    )
    chinese_bigrams = tuple(
        "".join(chinese_characters[index : index + 2])
        for index in range(len(chinese_characters) - 1)
    )
    return tuple(latin_tokens) + chinese_bigrams
