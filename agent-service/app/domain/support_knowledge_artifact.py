from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.domain.support_knowledge import SupportKnowledgeSourceKind


SupportKnowledgeArtifactFormat = Literal[
    "html",
    "pdf",
    "docx",
    "xlsx",
    "pptx",
]


@dataclass(frozen=True)
class SupportKnowledgeArtifact:
    """An immutable local copy of a source before text extraction begins."""

    artifact_id: str
    source_reference: str
    source_kind: SupportKnowledgeSourceKind
    document_format: SupportKnowledgeArtifactFormat
    storage_relative_path: str
    byte_size: int
    content_sha256: str


class SupportKnowledgeArtifactStore(Protocol):
    def save(
        self,
        *,
        source_reference: str,
        source_kind: SupportKnowledgeSourceKind,
        original_filename: str,
        content: bytes,
    ) -> SupportKnowledgeArtifact:
        ...
