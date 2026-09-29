from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from app.application.support_knowledge_retrieval import _tokenize
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


@dataclass(frozen=True)
class SupportKnowledgeChunkSearchHit:
    chunk: SupportKnowledgeChunk
    score: float


class LexicalSupportKnowledgeChunkRetriever:
    """Small BM25 retriever that returns the exact matching source chunk."""

    def __init__(self, chunks: tuple[SupportKnowledgeChunk, ...]) -> None:
        self._chunks = chunks
        self._tokens_by_chunk = tuple(_tokenize(chunk.text) for chunk in chunks)
        self._document_frequencies = Counter(
            token for tokens in self._tokens_by_chunk for token in set(tokens)
        )
        self._average_length = (
            sum(len(tokens) for tokens in self._tokens_by_chunk) / len(chunks)
            if chunks else 0.0
        )

    def search(
        self, query: str, *, top_k: int = 3
    ) -> tuple[SupportKnowledgeChunkSearchHit, ...]:
        if not query.strip():
            raise ValueError("support knowledge chunk search query must not be blank")
        if top_k <= 0:
            raise ValueError("support knowledge chunk search top_k must be positive")
        query_tokens = _tokenize(query)
        hits = tuple(
            SupportKnowledgeChunkSearchHit(chunk, self._score(query_tokens, tokens))
            for chunk, tokens in zip(self._chunks, self._tokens_by_chunk, strict=True)
        )
        return tuple(
            hit
            for hit in sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))
            if hit.score > 0
        )[:top_k]

    def _score(self, query_tokens: tuple[str, ...], tokens: tuple[str, ...]) -> float:
        if not query_tokens or not tokens or not self._chunks:
            return 0.0
        term_frequencies = Counter(tokens)
        score = 0.0
        for token in set(query_tokens):
            document_frequency = self._document_frequencies.get(token, 0)
            if not document_frequency:
                continue
            idf = math.log(
                1 + (len(self._chunks) - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            tf = term_frequencies.get(token, 0)
            normalized_tf = tf * 2.2 / (
                tf + 1.2 * (0.25 + 0.75 * len(tokens) / self._average_length)
            )
            score += idf * normalized_tf
        return score
