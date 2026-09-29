from __future__ import annotations

from collections.abc import Iterable

from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
    SupportKnowledgeArtifactParser,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class SupportKnowledgeParserNotRegisteredError(RuntimeError):
    """No parser has been configured for an artifact format."""


class DuplicateSupportKnowledgeParserError(ValueError):
    """Only one parser may own a document format in one registry."""


class SupportKnowledgeParserRegistry:
    def __init__(self, parsers: Iterable[SupportKnowledgeArtifactParser]) -> None:
        self._parsers_by_format = {}
        for parser in parsers:
            document_format = parser.document_format
            if document_format in self._parsers_by_format:
                raise DuplicateSupportKnowledgeParserError(
                    f"duplicate parser registration for format: {document_format}"
                )
            self._parsers_by_format[document_format] = parser

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        try:
            parser = self._parsers_by_format[artifact.document_format]
        except KeyError as error:
            raise SupportKnowledgeParserNotRegisteredError(
                "no parser registered for artifact format: "
                f"{artifact.document_format}"
            ) from error
        return parser.parse(artifact)

    def close(self) -> None:
        for parser in self._parsers_by_format.values():
            close = getattr(parser, "close", None)
            if callable(close):
                close()
