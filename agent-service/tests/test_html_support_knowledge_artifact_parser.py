from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.html_support_knowledge_artifact_parser import (
    HtmlSupportKnowledgeArtifactParser,
    SupportKnowledgeArtifactParseError,
)


class HtmlSupportKnowledgeArtifactParserTest(TestCase):
    def test_extracts_title_and_visible_text_without_script_or_style_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "guide.html").write_text(
                """<html><head><title>Network Guide</title><style>.hidden {}</style></head>
                <body><h1>Campus network</h1><p>Restart the client.</p>
                <script>secret = 'not evidence'</script></body></html>""",
                encoding="utf-8",
            )
            parsed = HtmlSupportKnowledgeArtifactParser(root).parse(
                _artifact("guide.html")
            )

        self.assertEqual("Network Guide", parsed.title)
        self.assertEqual("Network Guide Campus network Restart the client.", parsed.text)
        self.assertNotIn("not evidence", parsed.text)

    def test_rejects_an_html_artifact_with_no_extractable_text(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "blank.html").write_text(
                "<script>only_code()</script>",
                encoding="utf-8",
            )
            with self.assertRaises(SupportKnowledgeArtifactParseError):
                HtmlSupportKnowledgeArtifactParser(root).parse(
                    _artifact("blank.html")
                )


def _artifact(storage_relative_path: str) -> SupportKnowledgeArtifact:
    return SupportKnowledgeArtifact(
        artifact_id="artifact_demo",
        source_reference="https://it.example.edu/guide",
        source_kind="official_campus",
        document_format="html",
        storage_relative_path=storage_relative_path,
        byte_size=1,
        content_sha256="a" * 64,
    )
