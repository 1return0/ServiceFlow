from __future__ import annotations

import math
from typing import Any

import httpx

from app.domain.dense_support_knowledge_index import DenseEmbeddingIdentity


class DenseEmbeddingUnavailableError(RuntimeError):
    """A configured embedding endpoint could not produce a trustworthy vector."""

    def __init__(self, failure_code: str) -> None:
        super().__init__("embedding model call could not be completed")
        self.failure_code = failure_code


class QwenOpenAICompatibleTextEmbedder:
    """Adapts a Qwen OpenAI-compatible embedding endpoint to the domain protocol."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        revision: str,
        dimension: int,
        http_client: httpx.Client,
        batch_size: int = 20,
    ) -> None:
        if not base_url.strip() or not api_key.strip() or not model.strip():
            raise ValueError("embedding base_url, api_key and model must be non-blank")
        if not revision.strip():
            raise ValueError("embedding revision must be non-blank")
        if dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        if batch_size <= 0:
            raise ValueError("embedding batch_size must be positive")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._batch_size = batch_size
        self._http_client = http_client
        self._embedding_identity = DenseEmbeddingIdentity(
            provider="qwen-openai-compatible",
            model=model,
            revision=revision,
            dimension=dimension,
        )

    @property
    def embedding_identity(self) -> DenseEmbeddingIdentity:
        return self._embedding_identity

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        if any(not text.strip() for text in texts):
            raise ValueError("embedding documents must be non-blank")
        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(self._embed(texts[start : start + self._batch_size]))
        return tuple(vectors)

    def embed_query(self, text: str) -> tuple[float, ...]:
        if not text.strip():
            raise ValueError("embedding query must be non-blank")
        return self._embed((text,))[0]

    def close(self) -> None:
        self._http_client.close()

    def _embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        try:
            response = self._http_client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "input": list(texts),
                    "dimensions": self._embedding_identity.dimension,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            return _read_vectors(
                response.json(),
                expected_count=len(texts),
                expected_dimension=self._embedding_identity.dimension,
            )
        except httpx.TimeoutException as error:
            raise DenseEmbeddingUnavailableError("embedding-model-timeout") from error
        except httpx.HTTPStatusError as error:
            raise DenseEmbeddingUnavailableError(
                _http_failure_code(error.response)
            ) from error
        except httpx.RequestError as error:
            raise DenseEmbeddingUnavailableError("embedding-model-network-error") from error
        except (KeyError, TypeError, ValueError) as error:
            raise DenseEmbeddingUnavailableError(
                "embedding-model-invalid-response"
            ) from error


def _read_vectors(
    payload: dict[str, Any],
    *,
    expected_count: int,
    expected_dimension: int,
) -> tuple[tuple[float, ...], ...]:
    entries = payload["data"]
    if not isinstance(entries, list) or len(entries) != expected_count:
        raise ValueError("embedding response count does not match input")
    indexed_vectors: dict[int, tuple[float, ...]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("embedding response entry must be an object")
        index = entry["index"]
        raw_vector = entry["embedding"]
        if not isinstance(index, int) or index < 0 or index >= expected_count:
            raise ValueError("embedding response index is invalid")
        if index in indexed_vectors or not isinstance(raw_vector, list):
            raise ValueError("embedding response contains duplicate or invalid vectors")
        vector = tuple(float(value) for value in raw_vector)
        if (
            len(vector) != expected_dimension
            or not all(math.isfinite(value) for value in vector)
            or not any(value != 0.0 for value in vector)
        ):
            raise ValueError("embedding response vector is invalid")
        indexed_vectors[index] = vector
    if set(indexed_vectors) != set(range(expected_count)):
        raise ValueError("embedding response indexes do not cover the input")
    return tuple(indexed_vectors[index] for index in range(expected_count))


def _http_failure_code(response: httpx.Response) -> str:
    if _provider_error_code(response) == "insufficient_quota":
        return "embedding-model-insufficient-quota"
    if response.status_code in {401, 403}:
        return "embedding-model-authentication-failed"
    if response.status_code == 404:
        return "embedding-model-endpoint-or-model-not-found"
    if response.status_code == 429:
        return "embedding-model-rate-limited"
    if 500 <= response.status_code <= 599:
        return "embedding-model-server-error"
    return "embedding-model-http-error"


def _provider_error_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) and code else None
