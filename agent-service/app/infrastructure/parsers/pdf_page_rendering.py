from __future__ import annotations

import math
from dataclasses import dataclass


class PdfPagePixelLimitExceededError(ValueError):
    """A PDF page would create an unsafe number of raster pixels."""


@dataclass(frozen=True)
class PdfPageRasterizationSettings:
    """Safety limits that apply before any OCR image is rendered."""

    dpi: int = 144
    max_page_pixels: int = 8_000_000

    def __post_init__(self) -> None:
        if self.dpi <= 0:
            raise ValueError("dpi must be positive")
        if self.max_page_pixels <= 0:
            raise ValueError("max_page_pixels must be positive")


@dataclass(frozen=True)
class PdfPageRenderPlan:
    page_number: int
    width_pixels: int
    height_pixels: int
    pixel_count: int
    dpi: int


class PdfPageRasterizationPlanner:
    """Calculates safe page dimensions before a renderer allocates an image."""

    def __init__(self, settings: PdfPageRasterizationSettings) -> None:
        self._settings = settings

    def plan_page(
        self,
        *,
        page_number: int,
        width_points: float,
        height_points: float,
    ) -> PdfPageRenderPlan:
        if page_number < 1:
            raise ValueError("page_number must be at least 1")
        if width_points <= 0 or height_points <= 0:
            raise ValueError("PDF page dimensions must be positive")

        scale = self._settings.dpi / 72
        width_pixels = math.ceil(width_points * scale)
        height_pixels = math.ceil(height_points * scale)
        pixel_count = width_pixels * height_pixels
        if pixel_count > self._settings.max_page_pixels:
            raise PdfPagePixelLimitExceededError(
                "PDF page exceeds configured raster pixel limit: "
                f"page={page_number}, pixels={pixel_count}, "
                f"limit={self._settings.max_page_pixels}"
            )
        return PdfPageRenderPlan(
            page_number=page_number,
            width_pixels=width_pixels,
            height_pixels=height_pixels,
            pixel_count=pixel_count,
            dpi=self._settings.dpi,
        )
