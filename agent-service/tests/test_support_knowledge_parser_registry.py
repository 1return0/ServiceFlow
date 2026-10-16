from __future__ import annotations

from dataclasses import dataclass
from unittest import TestCase

from app.application.knowledge.support_knowledge_parser_registry import (
    DuplicateSupportKnowledgeParserError,
    SupportKnowledgeParserNotRegisteredError,
    SupportKnowledgeParserRegistry,
)
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class SupportKnowledgeParserRegistryTest(TestCase):
    def test_routes_an_html_artifact_to_its_registered_parser(self) -> None:
        parser = _StubHtmlParser()
        registry = SupportKnowledgeParserRegistry([parser])

        parsed = registry.parse(_artifact(document_format="html"))

        self.assertTrue(parser.was_called)
        self.assertEqual("Parsed HTML", parsed.text)

    def test_rejects_an_artifact_for_an_unregistered_format(self) -> None:
        registry = SupportKnowledgeParserRegistry([_StubHtmlParser()])

        with self.assertRaises(SupportKnowledgeParserNotRegisteredError):
            registry.parse(_artifact(document_format="pdf"))

    def test_rejects_two_parsers_for_the_same_format(self) -> None:
        with self.assertRaises(DuplicateSupportKnowledgeParserError):
            SupportKnowledgeParserRegistry([_StubHtmlParser(), _StubHtmlParser()])


@dataclass
class _StubHtmlParser:
    was_called: bool = False

    @property
    def document_format(self) -> str:
        return "html"

    def parse(self, artifact: SupportKnowledgeArtifact) -> ParsedSupportKnowledgeDocument:
        self.was_called = True
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="html",
            title="Stub",
            text="Parsed HTML",
        )


def _artifact(*, document_format: str) -> SupportKnowledgeArtifact:
    return SupportKnowledgeArtifact(
        artifact_id="artifact_demo",
        source_reference="https://it.example.edu/guide",
        source_kind="official_campus",
        document_format=document_format,  # type: ignore[arg-type]
        storage_relative_path="guide.html",
        byte_size=1,
        content_sha256="a" * 64,
    )
