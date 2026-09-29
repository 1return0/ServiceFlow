from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeFragment,
    ParsedSupportKnowledgeDocument,
    SupportKnowledgeArtifactParseError,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class DocxSupportKnowledgeArtifactParser:
    """Extracts the basic visible text and table cells from a DOCX artifact."""

    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root.resolve()

    @property
    def document_format(self) -> str:
        return "docx"

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        if artifact.document_format != self.document_format:
            raise SupportKnowledgeArtifactParseError(
                "DOCX parser received a non-DOCX artifact"
            )
        path = self._resolve_artifact_path(artifact.storage_relative_path)
        try:
            document = Document(path)
        except (OSError, ValueError, BadZipFile, PackageNotFoundError) as error:
            raise SupportKnowledgeArtifactParseError(
                "DOCX artifact could not be read"
            ) from error

        fragments_list: list[ParsedSupportKnowledgeFragment] = []
        for block_ordinal, (block_kind, block) in enumerate(
            _iter_document_blocks(document), start=1
        ):
            for text_ordinal, text in enumerate(_block_texts(block), start=1):
                fragments_list.append(
                    ParsedSupportKnowledgeFragment(
                        ordinal=len(fragments_list) + 1,
                        location=(
                            f"{block_kind}:{block_ordinal}:item:{text_ordinal}"
                        ),
                        text=text,
                    )
                )
        fragments = tuple(fragments_list)
        text = "\n".join(fragment.text for fragment in fragments)
        if not text:
            raise SupportKnowledgeArtifactParseError(
                "DOCX artifact contains no extractable text"
            )
        title = (document.core_properties.title or "").strip() or None
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="docx",
            title=title,
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


def _iter_document_blocks(document: Document):
    """Yield top-level paragraphs and tables in the XML order they appear."""
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield "paragraph", Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield "table", Table(child, document)


def _block_texts(block: Paragraph | Table) -> tuple[str, ...]:
    if isinstance(block, Paragraph):
        text = block.text.strip()
        return (text,) if text else ()
    return tuple(
        " | ".join(
            cell.text.strip()
            for cell in row.cells
            if cell.text.strip()
        )
        for row in block.rows
        if any(cell.text.strip() for cell in row.cells)
    )
