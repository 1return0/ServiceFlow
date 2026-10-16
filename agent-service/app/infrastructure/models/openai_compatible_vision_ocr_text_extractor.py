from __future__ import annotations

import base64
from typing import Any

import httpx

from app.domain.ocr_text_extraction import (
    OcrPageText,
    PdfPageRenderer,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class OcrTextExtractorUnavailableError(RuntimeError):
    """The configured vision OCR endpoint could not recognise a PDF page."""

    def __init__(self, failure_code: str) -> None:
        super().__init__("OCR text extraction could not be completed")
        self.failure_code = failure_code


class OpenAiCompatibleVisionOcrTextExtractor:
    """Call an OpenAI-compatible vision model once for each rendered PDF page."""

    prompt_version = "campus-support-ocr-prompt-v1"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        page_renderer: PdfPageRenderer,
        http_client: httpx.Client,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._page_renderer = page_renderer
        self._http_client = http_client

    @property
    def identity(self) -> str:
        return (
            f"openai-compatible-vision-ocr:{self._model}:"
            f"{self.prompt_version}"
        )

    def extract_page_texts(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> tuple[OcrPageText, ...]:
        return tuple(
            OcrPageText(
                page_number=page.page_number,
                text=self._recognise_page(page.png_bytes),
            )
            for page in self._page_renderer.render_pages(artifact)
        )

    def _recognise_page(self, png_bytes: bytes) -> str:
        data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode(
            "ascii"
        )
        try:
            response = self._http_client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You perform OCR for campus service documents. "
                                "Return only visible text in reading order. "
                                "Do not explain, summarise, infer, or use Markdown."
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Recognise all visible text in this PDF page.",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url},
                                },
                            ],
                        },
                    ],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            return _read_completion_content(response.json())
        except httpx.TimeoutException as error:
            raise OcrTextExtractorUnavailableError("ocr-model-timeout") from error
        except httpx.HTTPStatusError as error:
            raise OcrTextExtractorUnavailableError(
                _http_failure_code(error.response)
            ) from error
        except httpx.RequestError as error:
            raise OcrTextExtractorUnavailableError("ocr-model-network-error") from error
        except (KeyError, TypeError, ValueError) as error:
            raise OcrTextExtractorUnavailableError("ocr-model-invalid-response") from error

    def close(self) -> None:
        self._http_client.close()


def _read_completion_content(payload: dict[str, Any]) -> str:
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OCR response content must be a non-blank string")
    return content.strip()


def _http_failure_code(response: httpx.Response) -> str:
    if response.status_code in {401, 403}:
        return "ocr-model-authentication-failed"
    if response.status_code == 404:
        return "ocr-model-endpoint-or-model-not-found"
    if response.status_code == 429:
        return "ocr-model-rate-limited"
    if 500 <= response.status_code <= 599:
        return "ocr-model-server-error"
    return "ocr-model-http-error"
