from __future__ import annotations

import json
import unittest

import httpx

from app.infrastructure.models.qwen_openai_compatible_text_embedder import (
    DenseEmbeddingUnavailableError,
    QwenOpenAICompatibleTextEmbedder,
)


class QwenOpenAICompatibleTextEmbedderTest(unittest.TestCase):
    def test_embeds_documents_in_input_order_even_when_provider_order_differs(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("Bearer test-key", request.headers["Authorization"])
            self.assertEqual("/compatible-mode/v1/embeddings", request.url.path)
            payload = json.loads(request.content)
            self.assertEqual("qwen3.7-text-embedding-flash", payload["model"])
            self.assertEqual(["网络", "图书馆"], payload["input"])
            self.assertEqual(2, payload["dimensions"])
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"index": 1, "embedding": [0.0, 1.0]},
                        {"index": 0, "embedding": [1.0, 0.0]},
                    ]
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            embedder = _embedder(http_client)
            vectors = embedder.embed_documents(("网络", "图书馆"))

        self.assertEqual(((1.0, 0.0), (0.0, 1.0)), vectors)
        self.assertEqual("qwen-openai-compatible", embedder.embedding_identity.provider)
        self.assertEqual(2, embedder.embedding_identity.dimension)

    def test_batches_documents_and_embeds_query_without_document_reuse(self) -> None:
        received_inputs: list[list[str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            received_inputs.append(payload["input"])
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"index": index, "embedding": [float(index + 1), 1.0]}
                        for index, _text in enumerate(payload["input"])
                    ]
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            embedder = _embedder(http_client, batch_size=2)
            documents = embedder.embed_documents(("a", "b", "c"))
            query = embedder.embed_query("查询")

        self.assertEqual([["a", "b"], ["c"], ["查询"]], received_inputs)
        self.assertEqual(3, len(documents))
        self.assertEqual((1.0, 1.0), query)

    def test_normalizes_embedding_authentication_failure(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(403))
        ) as http_client:
            with self.assertRaises(DenseEmbeddingUnavailableError) as raised:
                _embedder(http_client).embed_query("校园网")

        self.assertEqual("embedding-model-authentication-failed", raised.exception.failure_code)

    def test_rejects_wrong_dimension_in_provider_response(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"data": [{"index": 0, "embedding": [1.0]}]},
                )
            )
        ) as http_client:
            with self.assertRaises(DenseEmbeddingUnavailableError) as raised:
                _embedder(http_client).embed_query("校园网")

        self.assertEqual("embedding-model-invalid-response", raised.exception.failure_code)


def _embedder(
    http_client: httpx.Client,
    *,
    batch_size: int = 20,
) -> QwenOpenAICompatibleTextEmbedder:
    return QwenOpenAICompatibleTextEmbedder(
        base_url="https://example.test/compatible-mode/v1",
        api_key="test-key",
        model="qwen3.7-text-embedding-flash",
        revision="test-revision",
        dimension=2,
        batch_size=batch_size,
        http_client=http_client,
    )


if __name__ == "__main__":
    unittest.main()
