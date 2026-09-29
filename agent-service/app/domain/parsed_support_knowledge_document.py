from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.support_knowledge_artifact import (
    SupportKnowledgeArtifact,
    SupportKnowledgeArtifactFormat,
)


class SupportKnowledgeArtifactParseError(RuntimeError):
    """A stored raw artifact could not be converted into usable text."""


@dataclass(frozen=True)
class ParsedSupportKnowledgeFragment:
    ordinal: int
    location: str
    text: str


@dataclass(frozen=True)
class ParsedSupportKnowledgeDocument:
    artifact_id: str
    document_format: SupportKnowledgeArtifactFormat
    title: str | None
    text: str
    fragments: tuple[ParsedSupportKnowledgeFragment, ...] = ()


class SupportKnowledgeArtifactParser(Protocol):
    @property
    def document_format(self) -> SupportKnowledgeArtifactFormat:
        ...

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        ...
