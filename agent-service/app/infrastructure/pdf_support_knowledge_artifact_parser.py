from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeFragment,
    ParsedSupportKnowledgeDocument,
    SupportKnowledgeArtifactParseError,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class PdfTextLayerMissingError(SupportKnowledgeArtifactParseError):
    """The PDF is readable but exposes no extractable text layer."""


class PdfSupportKnowledgeArtifactParser:
    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root.resolve()

    @property
    def document_format(self) -> str:
        return "pdf"

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        if artifact.document_format != self.document_format:
            raise SupportKnowledgeArtifactParseError(
                "PDF parser received a non-PDF artifact"
            )
        path = self._resolve_artifact_path(artifact.storage_relative_path)
        try:
            reader = PdfReader(path)
            page_texts = tuple(page.extract_text() or "" for page in reader.pages)
        except (OSError, PdfReadError) as error:
            raise SupportKnowledgeArtifactParseError(
                "PDF artifact could not be read"
            ) from error

        fragments = tuple(
            ParsedSupportKnowledgeFragment(
                ordinal=index,
                location=f"page:{index}",
                text=page_text.strip(),
            )
            for index, page_text in enumerate(page_texts, start=1)
            if page_text.strip()
        )
        text = "\n".join(fragment.text for fragment in fragments)
        if not text:
            raise PdfTextLayerMissingError(
                "PDF artifact has no extractable text layer"
            )
        metadata = reader.metadata
        title = metadata.title.strip() if metadata and metadata.title else None
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="pdf",
            title=title or None,
            text=text,
            fragments=fragments,
        )

    def _resolve_artifact_path(self, storage_relative_path: str) -> Path:
        path = (self._artifact_root / storage_relative_path).resolve()
        if self._artifact_root not in path.parents:
            raise SupportKnowledgeArtifactParseError(
                "artifact path escaped the configured artifact root"
            )
        return path
