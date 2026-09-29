from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pypdf import PdfWriter

from app.domain.ocr_text_extraction import OcrPageText
from app.application.ocr_page_reading_order import OcrPageSequenceError
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.pdf_ocr_fallback_support_knowledge_artifact_parser import (
    OcrTextExtractionEmptyError,
    PdfOcrFallbackSupportKnowledgeArtifactParser,
)
from app.infrastructure.pdf_support_knowledge_artifact_parser import (
    PdfSupportKnowledgeArtifactParser,
)


class PdfOcrFallbackSupportKnowledgeArtifactParserTest(TestCase):
    def test_uses_ocr_only_when_a_readable_pdf_has_no_text_layer(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with (root / "scan.pdf").open("wb") as stream:
                writer.write(stream)
            extractor = _StubOcrTextExtractor(
                (OcrPageText(page_number=1, text="校园网报修请联系服务台"),)
            )
            parser = PdfOcrFallbackSupportKnowledgeArtifactParser(
                PdfSupportKnowledgeArtifactParser(root), extractor
            )

            parsed = parser.parse(_artifact("scan.pdf"))

        self.assertEqual(1, extractor.call_count)
        self.assertEqual("校园网报修请联系服务台", parsed.text)
        self.assertEqual("page:1:ocr", parsed.fragments[0].location)

    def test_does_not_hide_a_broken_pdf_behind_ocr(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.pdf").write_bytes(b"not a pdf")
            extractor = _StubOcrTextExtractor((OcrPageText(1, "unexpected"),))
            parser = PdfOcrFallbackSupportKnowledgeArtifactParser(
                PdfSupportKnowledgeArtifactParser(root), extractor
            )

            with self.assertRaises(Exception):
                parser.parse(_artifact("broken.pdf"))

        self.assertEqual(0, extractor.call_count)

    def test_rejects_empty_ocr_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with (root / "scan.pdf").open("wb") as stream:
                writer.write(stream)
            parser = PdfOcrFallbackSupportKnowledgeArtifactParser(
                PdfSupportKnowledgeArtifactParser(root),
                _StubOcrTextExtractor((OcrPageText(1, "   "),)),
            )

            with self.assertRaises(OcrTextExtractionEmptyError):
                parser.parse(_artifact("scan.pdf"))

    def test_restores_pdf_page_order_before_creating_fragments(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with (root / "scan.pdf").open("wb") as stream:
                writer.write(stream)
            parser = PdfOcrFallbackSupportKnowledgeArtifactParser(
                PdfSupportKnowledgeArtifactParser(root),
                _StubOcrTextExtractor(
                    (
                        OcrPageText(page_number=2, text="第二页"),
                        OcrPageText(page_number=1, text="第一页"),
                    )
                ),
            )

            parsed = parser.parse(_artifact("scan.pdf"))

        self.assertEqual("第一页\n第二页", parsed.text)
        self.assertEqual(
            ("page:1:ocr", "page:2:ocr"),
            tuple(fragment.location for fragment in parsed.fragments),
        )

    def test_rejects_duplicate_page_numbers_from_ocr(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with (root / "scan.pdf").open("wb") as stream:
                writer.write(stream)
            parser = PdfOcrFallbackSupportKnowledgeArtifactParser(
                PdfSupportKnowledgeArtifactParser(root),
                _StubOcrTextExtractor(
                    (
                        OcrPageText(page_number=1, text="A"),
                        OcrPageText(page_number=1, text="B"),
                    )
                ),
            )

            with self.assertRaises(OcrPageSequenceError):
                parser.parse(_artifact("scan.pdf"))


class _StubOcrTextExtractor:
    def __init__(self, pages: tuple[OcrPageText, ...]) -> None:
        self._pages = pages
        self.call_count = 0

    def extract_page_texts(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> tuple[OcrPageText, ...]:
        self.call_count += 1
        return self._pages


def _artifact(storage_relative_path: str) -> SupportKnowledgeArtifact:
    return SupportKnowledgeArtifact(
        artifact_id="artifact_pdf",
        source_reference="https://it.example.edu/guide.pdf",
        source_kind="official_campus",
        document_format="pdf",
        storage_relative_path=storage_relative_path,
        byte_size=1,
        content_sha256="a" * 64,
    )
