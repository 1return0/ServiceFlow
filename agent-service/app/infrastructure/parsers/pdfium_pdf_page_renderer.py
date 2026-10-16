from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium

from app.domain.ocr_text_extraction import RenderedPdfPage
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.parsers.pdf_page_rendering import PdfPageRasterizationPlanner


class PdfPageRenderError(RuntimeError):
    """A readable PDF page could not be safely rendered to an OCR image."""


class PdfiumPdfPageRenderer:
    """Render PDF pages to PNG only after page dimensions pass the pixel guard."""

    def __init__(
        self,
        artifact_root: Path,
        planner: PdfPageRasterizationPlanner,
    ) -> None:
        self._artifact_root = artifact_root.resolve()
        self._planner = planner

    def render_pages(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> tuple[RenderedPdfPage, ...]:
        if artifact.document_format != "pdf":
            raise PdfPageRenderError("PDF renderer received a non-PDF artifact")
        path = self._resolve_artifact_path(artifact.storage_relative_path)
        try:
            document = pdfium.PdfDocument(path)
        except (OSError, pdfium.PdfiumError) as error:
            raise PdfPageRenderError("PDF artifact could not be opened for rendering") from error

        rendered_pages: list[RenderedPdfPage] = []
        try:
            for page_number in range(1, len(document) + 1):
                page = document[page_number - 1]
                try:
                    width_points, height_points = page.get_size()
                    plan = self._planner.plan_page(
                        page_number=page_number,
                        width_points=width_points,
                        height_points=height_points,
                    )
                    bitmap = page.render(scale=plan.dpi / 72)
                    try:
                        image = bitmap.to_pil()
                        try:
                            with BytesIO() as output:
                                image.save(output, format="PNG")
                                png_bytes = output.getvalue()
                        finally:
                            image.close()
                    finally:
                        bitmap.close()
                    rendered_pages.append(
                        RenderedPdfPage(
                            page_number=page_number,
                            width_pixels=plan.width_pixels,
                            height_pixels=plan.height_pixels,
                            png_bytes=png_bytes,
                        )
                    )
                finally:
                    page.close()
        except (OSError, pdfium.PdfiumError) as error:
            raise PdfPageRenderError("PDF page could not be rendered") from error
        finally:
            document.close()
        return tuple(rendered_pages)

    def _resolve_artifact_path(self, storage_relative_path: str) -> Path:
        path = (self._artifact_root / storage_relative_path).resolve()
        if self._artifact_root not in path.parents:
            raise PdfPageRenderError("artifact path escaped the configured artifact root")
        return path
