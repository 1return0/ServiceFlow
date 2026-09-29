from __future__ import annotations

from typing import Any

import httpx


class PlannerModelUnavailableError(RuntimeError):
    """The configured OpenAI-compatible model endpoint could not complete a plan."""

    def __init__(self, failure_code: str) -> None:
        super().__init__("planner model call could not be completed")
        self.failure_code = failure_code


class QwenOpenAICompatiblePlannerModel:
    """Infrastructure adapter for Qwen's OpenAI-compatible chat-completions API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        http_client: httpx.Client,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._http_client = http_client

    @property
    def identity(self) -> str:
        return f"qwen-openai-compatible:{self._model}"

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        try:
            response = self._http_client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query},
                    ],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            return _read_completion_content(response.json())
        except httpx.TimeoutException as error:
            raise PlannerModelUnavailableError("planner-model-timeout") from error
        except httpx.HTTPStatusError as error:
            raise PlannerModelUnavailableError(
                _http_failure_code(error.response)
            ) from error
        except httpx.RequestError as error:
            raise PlannerModelUnavailableError("planner-model-network-error") from error
        except (KeyError, TypeError, ValueError) as error:
            raise PlannerModelUnavailableError("planner-model-invalid-response") from error

    def close(self) -> None:
        self._http_client.close()


def _read_completion_content(payload: dict[str, Any]) -> str:
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("planner model response content must be a non-blank string")
    return content


def _http_failure_code(response: httpx.Response) -> str:
    if _provider_error_code(response) == "insufficient_quota":
        return "planner-model-insufficient-quota"

    status_code = response.status_code
    if status_code in {401, 403}:
        return "planner-model-authentication-failed"
    if status_code == 404:
        return "planner-model-endpoint-or-model-not-found"
    if status_code == 429:
        return "planner-model-rate-limited"
    if 500 <= status_code <= 599:
        return "planner-model-server-error"
    return "planner-model-http-error"


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
