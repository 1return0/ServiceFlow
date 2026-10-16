from __future__ import annotations

from unittest import TestCase

from app.application.evaluation.ocr_smoke import run_ocr_smoke
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
    ParsedSupportKnowledgeFragment,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class OcrSmokeTest(TestCase):
    def test_records_identity_elapsed_time_and_ocr_locations(self) -> None:
        report = run_ocr_smoke(
            parser=_StubOcrParser(),
            artifact=_artifact(),
            recognizer_identity="vision:test:prompt-v1",
        )

        self.assertEqual("vision:test:prompt-v1", report.recognizer_identity)
        self.assertEqual(("page:1:ocr",), report.fragment_locations)
        self.assertGreaterEqual(report.elapsed_seconds, 0.0)

    def test_rejects_a_smoke_that_did_not_use_the_ocr_fallback(self) -> None:
        with self.assertRaisesRegex(ValueError, "OCR fallback"):
            run_ocr_smoke(
                parser=_StubOcrParser(location="page:1"),
                artifact=_artifact(),
                recognizer_identity="vision:test:prompt-v1",
            )


class _StubOcrParser:
    def __init__(self, *, location: str = "page:1:ocr") -> None:
        self._location = location

    def parse(self, artifact: SupportKnowledgeArtifact) -> ParsedSupportKnowledgeDocument:
        return ParsedSupportKnowledgeDocument(
            artifact_id=artifact.artifact_id,
            document_format="pdf",
            title=None,
            text="Campus IT Support",
            fragments=(ParsedSupportKnowledgeFragment(1, self._location, "Campus IT Support"),),
        )


def _artifact() -> SupportKnowledgeArtifact:
    return SupportKnowledgeArtifact(
        artifact_id="artifact-smoke",
        source_reference="synthetic://ocr-smoke",
        source_kind="demonstration",
        document_format="pdf",
        storage_relative_path="synthetic-scan.pdf",
        byte_size=1,
        content_sha256="a" * 64,
    )
