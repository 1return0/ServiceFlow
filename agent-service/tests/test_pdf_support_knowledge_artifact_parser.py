from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from app.domain.parsed_support_knowledge_document import (
    SupportKnowledgeArtifactParseError,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.parsers.pdf_support_knowledge_artifact_parser import (
    PdfSupportKnowledgeArtifactParser,
    PdfTextLayerMissingError,
)


class PdfSupportKnowledgeArtifactParserTest(TestCase):
    def test_extracts_text_and_title_from_a_text_layer_pdf(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_pdf_with_text(root / "guide.pdf", "Campus network guide")

            parsed = PdfSupportKnowledgeArtifactParser(root).parse(
                _artifact("guide.pdf")
            )

        self.assertEqual("Network Guide", parsed.title)
        self.assertEqual("Campus network guide", parsed.text)

    def test_distinguishes_a_missing_text_layer_from_a_broken_pdf(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with (root / "scan.pdf").open("wb") as stream:
                writer.write(stream)

            with self.assertRaises(PdfTextLayerMissingError):
                PdfSupportKnowledgeArtifactParser(root).parse(_artifact("scan.pdf"))

    def test_rejects_a_broken_pdf_as_a_file_read_error(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.pdf").write_bytes(b"not a pdf")

            with self.assertRaises(SupportKnowledgeArtifactParseError) as raised:
                PdfSupportKnowledgeArtifactParser(root).parse(_artifact("broken.pdf"))

        self.assertNotIsInstance(raised.exception, PdfTextLayerMissingError)


def _write_pdf_with_text(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(content)
    writer.add_metadata({"/Title": "Network Guide"})
    with path.open("wb") as stream:
        writer.write(stream)


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
