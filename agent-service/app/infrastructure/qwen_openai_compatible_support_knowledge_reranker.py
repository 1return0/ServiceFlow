from __future__ import annotations

import math

import httpx

from app.domain.support_knowledge_reranker import (
    SupportKnowledgeRerankerIdentity,
    SupportKnowledgeRerankResult,
)


class SupportKnowledgeRerankerUnavailableError(RuntimeError):
    def __init__(self, failure_code: str) -> None:
        super().__init__(failure_code)
        self.failure_code = failure_code


class QwenOpenAICompatibleSupportKnowledgeReranker:
    """Small adapter for the provider's OpenAI-compatible /reranks contract."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        revision: str,
        http_client: httpx.Client,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/reranks"
        self._api_key = api_key
        self._identity = SupportKnowledgeRerankerIdentity(
            provider="qwen-openai-compatible",
            model=model,
            revision=revision,
        )
        self._http_client = http_client

    @property
    def identity(self) -> SupportKnowledgeRerankerIdentity:
        return self._identity

    def rerank(
        self,
        query: str,
        documents: tuple[str, ...],
    ) -> tuple[SupportKnowledgeRerankResult, ...]:
        if not query.strip():
            raise ValueError("rerank query must not be blank")
        if not documents or any(not document.strip() for document in documents):
            raise ValueError("rerank documents must contain non-blank text")
        try:
            response = self._http_client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._identity.model,
                    "query": query,
                    "documents": list(documents),
                    "top_n": len(documents),
                },
            )
            response.raise_for_status()
            payload = response.json()
            return _read_results(payload, expected_count=len(documents))
        except httpx.TimeoutException as error:
            raise SupportKnowledgeRerankerUnavailableError("reranker-model-timeout") from error
        except httpx.HTTPStatusError as error:
            raise SupportKnowledgeRerankerUnavailableError(
                _http_failure_code(error.response)
            ) from error
        except httpx.RequestError as error:
            raise SupportKnowledgeRerankerUnavailableError("reranker-model-network-error") from error
        except (KeyError, TypeError, ValueError) as error:
            raise SupportKnowledgeRerankerUnavailableError("reranker-model-invalid-response") from error

    def close(self) -> None:
        self._http_client.close()


def _read_results(
    payload: object,
    *,
    expected_count: int,
) -> tuple[SupportKnowledgeRerankResult, ...]:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("rerank response must contain results")
    result_rows = payload["results"]
    results: list[SupportKnowledgeRerankResult] = []
    seen_indices: set[int] = set()
    for row in result_rows:
        if not isinstance(row, dict):
            raise ValueError("rerank result must be an object")
        index = row.get("index")
        score = row.get("relevance_score")
        if (
            not isinstance(index, int)
            or index < 0
            or index >= expected_count
            or index in seen_indices
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
        ):
            raise ValueError("rerank response contains an invalid result")
        seen_indices.add(index)
        results.append(SupportKnowledgeRerankResult(index, float(score)))
    if len(results) != expected_count or seen_indices != set(range(expected_count)):
        raise ValueError("rerank response must rank every candidate exactly once")
    return tuple(results)


def _http_failure_code(response: httpx.Response) -> str:
    if response.status_code in {401, 403}:
        return "reranker-model-authentication-failed"
    if response.status_code == 429:
        return "reranker-model-rate-limited"
    if response.status_code >= 500:
        return "reranker-model-server-error"
    return "reranker-model-request-rejected"
