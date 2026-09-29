from __future__ import annotations

import hashlib
from pathlib import Path

from app.domain.support_knowledge import SupportKnowledgeSourceKind
from app.domain.support_knowledge_artifact import (
    SupportKnowledgeArtifact,
    SupportKnowledgeArtifactFormat,
)


class SupportKnowledgeArtifactStoreError(RuntimeError):
    """A raw source file could not be stored safely."""


_FORMAT_BY_SUFFIX: dict[str, SupportKnowledgeArtifactFormat] = {
    ".html": "html",
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
}


class FileSystemSupportKnowledgeArtifactStore:
    """Content-addressed raw artifact storage, isolated from parsed RAG text."""

    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root.resolve()

    def save(
        self,
        *,
        source_reference: str,
        source_kind: SupportKnowledgeSourceKind,
        original_filename: str,
        content: bytes,
    ) -> SupportKnowledgeArtifact:
        normalized_name = self._normalize_filename(original_filename)
        document_format = self._resolve_format(normalized_name)
        content_sha256 = hashlib.sha256(content).hexdigest()
        storage_name = f"{content_sha256}.{document_format}"
        destination = self._artifact_root / storage_name

        try:
            self._artifact_root.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if destination.read_bytes() != content:
                    raise SupportKnowledgeArtifactStoreError(
                        "artifact storage hash collision detected"
                    )
            else:
                destination.write_bytes(content)
        except OSError as error:
            raise SupportKnowledgeArtifactStoreError(
                "support knowledge artifact could not be stored"
            ) from error

        return SupportKnowledgeArtifact(
            artifact_id=f"artifact_{content_sha256}",
            source_reference=source_reference,
            source_kind=source_kind,
            document_format=document_format,
            storage_relative_path=storage_name,
            byte_size=len(content),
            content_sha256=content_sha256,
        )

    @staticmethod
    def _normalize_filename(original_filename: str) -> str:
        candidate = original_filename.strip()
        path = Path(candidate)
        if not candidate or path.name != candidate:
            raise SupportKnowledgeArtifactStoreError(
                "artifact filename must be a single relative file name"
            )
        return candidate

    @staticmethod
    def _resolve_format(filename: str) -> SupportKnowledgeArtifactFormat:
        try:
            return _FORMAT_BY_SUFFIX[Path(filename).suffix.casefold()]
        except KeyError as error:
            raise SupportKnowledgeArtifactStoreError(
                "artifact format must be html, pdf, docx, xlsx, or pptx"
            ) from error
