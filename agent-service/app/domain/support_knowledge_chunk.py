from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupportKnowledgeChunk:
    chunk_id: str
    article_id: str
    text: str
    fragment_ordinal: int
    fragment_location: str
    fragment_char_start: int
    fragment_char_end: int
    chunker_version: str
