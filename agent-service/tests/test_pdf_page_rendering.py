from __future__ import annotations

from unittest import TestCase

from app.infrastructure.parsers.pdf_page_rendering import (
    PdfPagePixelLimitExceededError,
    PdfPageRasterizationPlanner,
    PdfPageRasterizationSettings,
)


class PdfPageRasterizationPlannerTest(TestCase):
    def test_converts_pdf_points_to_pixels_before_rendering(self) -> None:
        planner = PdfPageRasterizationPlanner(
            PdfPageRasterizationSettings(dpi=144, max_page_pixels=8_000_000)
        )

        plan = planner.plan_page(
            page_number=1,
            width_points=720,
            height_points=1440,
        )

        self.assertEqual(1440, plan.width_pixels)
        self.assertEqual(2880, plan.height_pixels)
        self.assertEqual(4_147_200, plan.pixel_count)

    def test_rejects_an_oversized_page_before_an_image_is_allocated(self) -> None:
        planner = PdfPageRasterizationPlanner(
            PdfPageRasterizationSettings(dpi=144, max_page_pixels=4_000_000)
        )

        with self.assertRaises(PdfPagePixelLimitExceededError):
            planner.plan_page(
                page_number=1,
                width_points=720,
                height_points=1440,
            )
