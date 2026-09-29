from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeFragment,
    ParsedSupportKnowledgeDocument,
    SupportKnowledgeArtifactParseError,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class _HtmlTextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._in_title = False
        self._ignored_depth = 0

    @property
    def title(self) -> str | None:
        return _normalize_text(" ".join(self._title_parts)) or None

    @property
    def text(self) -> str:
        return _normalize_text(" ".join(self._text_parts))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in {"script", "style"}:
            self._ignored_depth += 1
        elif normalized_tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif normalized_tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
        self._text_parts.append(data)


class HtmlSupportKnowledgeArtifactParser:
    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root.resolve()

    @property
    def document_format(self) -> str:
        return "html"

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        if artifact.document_format != self.document_format:
            raise SupportKnowledgeArtifactParseError(
                "HTML parser received a non-HTML artifact"
            )
        path = self._resolve_artifact_path(artifact.storage_relative_path)
        try:
            html = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise SupportKnowledgeArtifactParseError(
                "HTML artifact could not be read as UTF-8"
            ) from error

        collector = _HtmlTextCollector()
        collector.feed(html)
        if not collector.text:
            raise SupportKnowledgeArtifactParseError(
                "HTML artifact contains no extractable text"
            )
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="html",
            title=collector.title,
            text=collector.text,
            fragments=(
                ParsedSupportKnowledgeFragment(
                    ordinal=1,
                    location="html:body",
                    text=collector.text,
                ),
            ),
        )

    def _resolve_artifact_path(self, storage_relative_path: str) -> Path:
        path = (self._artifact_root / storage_relative_path).resolve()
        if self._artifact_root not in path.parents:
            raise SupportKnowledgeArtifactParseError(
                "artifact path escaped the configured artifact root"
            )
        return path


def _normalize_text(text: str) -> str:
    return " ".join(text.split())
