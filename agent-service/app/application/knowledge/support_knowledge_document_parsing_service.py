from __future__ import annotations

from app.application.knowledge.support_knowledge_parser_registry import (
    SupportKnowledgeParserRegistry,
)
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class SupportKnowledgeDocumentParsingService:
    """Application entry point for parsing already-stored knowledge artifacts."""

    def __init__(self, parser_registry: SupportKnowledgeParserRegistry) -> None:
        self._parser_registry = parser_registry

    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        return self._parser_registry.parse(artifact)

    def close(self) -> None:
        self._parser_registry.close()
