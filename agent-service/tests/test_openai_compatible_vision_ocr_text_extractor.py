from __future__ import annotations

import json
from unittest import TestCase

import httpx

from app.domain.ocr_text_extraction import RenderedPdfPage
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact
from app.infrastructure.models.openai_compatible_vision_ocr_text_extractor import (
    OpenAiCompatibleVisionOcrTextExtractor,
    OcrTextExtractorUnavailableError,
)


class OpenAiCompatibleVisionOcrTextExtractorTest(TestCase):
    def test_sends_each_rendered_page_as_a_png_data_url(self) -> None:
        observed_requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            observed_requests.append(request)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "校园网报修"}}]},
            )

        extractor = OpenAiCompatibleVisionOcrTextExtractor(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="qwen-ocr-test",
            page_renderer=_StubPageRenderer(),
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        result = extractor.extract_page_texts(_artifact())

        self.assertEqual(((1, "校园网报修"),), tuple((x.page_number, x.text) for x in result))
        self.assertEqual(1, len(observed_requests))
        self.assertEqual("Bearer test-key", observed_requests[0].headers["Authorization"])
        body = json.loads(observed_requests[0].content)
        image_url = body["messages"][1]["content"][1]["image_url"]["url"]
        self.assertTrue(image_url.startswith("data:image/png;base64,"))

    def test_normalises_an_unauthorised_provider_response(self) -> None:
        extractor = OpenAiCompatibleVisionOcrTextExtractor(
            base_url="https://example.test/v1",
            api_key="test-key",
            model="qwen-ocr-test",
            page_renderer=_StubPageRenderer(),
            http_client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(401, json={"error": "bad key"})
                )
            ),
        )

        with self.assertRaises(OcrTextExtractorUnavailableError) as raised:
            extractor.extract_page_texts(_artifact())

        self.assertEqual("ocr-model-authentication-failed", raised.exception.failure_code)


class _StubPageRenderer:
    def render_pages(self, artifact: SupportKnowledgeArtifact) -> tuple[RenderedPdfPage, ...]:
        return (
            RenderedPdfPage(
                page_number=1,
                width_pixels=10,
                height_pixels=10,
                png_bytes=b"fake-png",
            ),
        )


def _artifact() -> SupportKnowledgeArtifact:
    return SupportKnowledgeArtifact(
        artifact_id="artifact_pdf",
        source_reference="https://it.example.edu/guide.pdf",
        source_kind="official_campus",
        document_format="pdf",
        storage_relative_path="scan.pdf",
        byte_size=1,
        content_sha256="a" * 64,
    )
