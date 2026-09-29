from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pypdf import PdfWriter

from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.pdf_page_rendering import (
    PdfPagePixelLimitExceededError,
    PdfPageRasterizationPlanner,
    PdfPageRasterizationSettings,
)
from app.infrastructure.pdfium_pdf_page_renderer import PdfiumPdfPageRenderer


class PdfiumPdfPageRendererTest(TestCase):
    def test_renders_a_pdf_page_to_png_after_dimension_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_blank_pdf(root / "scan.pdf", width=72, height=144)
            renderer = PdfiumPdfPageRenderer(
                root,
                PdfPageRasterizationPlanner(
                    PdfPageRasterizationSettings(dpi=144, max_page_pixels=100_000)
                ),
            )

            pages = renderer.render_pages(_artifact("scan.pdf"))

        self.assertEqual(1, len(pages))
        self.assertEqual((144, 288), (pages[0].width_pixels, pages[0].height_pixels))
        self.assertTrue(pages[0].png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_rejects_an_oversized_page_before_rendering_it(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_blank_pdf(root / "large.pdf", width=720, height=1440)
            renderer = PdfiumPdfPageRenderer(
                root,
                PdfPageRasterizationPlanner(
                    PdfPageRasterizationSettings(dpi=144, max_page_pixels=4_000_000)
                ),
            )

            with self.assertRaises(PdfPagePixelLimitExceededError):
                renderer.render_pages(_artifact("large.pdf"))


def _write_blank_pdf(path: Path, *, width: int, height: int) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
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
