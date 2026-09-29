from __future__ import annotations

import hashlib
import math

from app.domain.parsed_support_knowledge_document import ParsedSupportKnowledgeDocument
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class SupportKnowledgeChunkingError(ValueError):
    pass


class FragmentAwareSupportKnowledgeChunker:
    """Splits structural fragments without losing their source location."""

    def __init__(
        self,
        *,
        version: str = "fragment-aware-v2",
        max_chars: int = 500,
        overlap_chars: int = 80,
    ) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if overlap_chars < 0 or overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be non-negative and below max_chars")
        self._version = version
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    def chunk(
        self,
        article: SupportKnowledgeArticle,
        parsed_document: ParsedSupportKnowledgeDocument,
    ) -> tuple[SupportKnowledgeChunk, ...]:
        if article.content != parsed_document.text:
            raise SupportKnowledgeChunkingError(
                "article content does not match the parsed document"
            )
        chunks: list[SupportKnowledgeChunk] = []
        for fragment in parsed_document.fragments:
            for start, end, text in self._split(fragment.text):
                chunks.append(
                    SupportKnowledgeChunk(
                        chunk_id=self._chunk_id(
                            article.article_id, fragment.ordinal, start, end, text
                        ),
                        article_id=article.article_id,
                        text=text,
                        fragment_ordinal=fragment.ordinal,
                        fragment_location=fragment.location,
                        fragment_char_start=start,
                        fragment_char_end=end,
                        chunker_version=self._version,
                    )
                )
        return tuple(chunks)

    def _split(self, text: str):
        start = 0
        while start < len(text):
            end = self._choose_end(text, start)
            yield start, end, text[start:end]
            if end == len(text):
                return
            start = max(end - self._overlap_chars, start + 1)

    def _choose_end(self, text: str, start: int) -> int:
        hard_end = min(start + self._max_chars, len(text))
        if hard_end == len(text):
            return hard_end
        minimum_end = start + math.ceil(self._max_chars * 0.5)
        for index in range(hard_end - 1, minimum_end - 1, -1):
            if text[index] in "\n。！？；.!?;":
                return index + 1
        return hard_end

    def _chunk_id(
        self, article_id: str, ordinal: int, start: int, end: int, text: str
    ) -> str:
        payload = f"{self._version}\n{article_id}\n{ordinal}\n{start}\n{end}\n{text}"
        return "chunk_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
