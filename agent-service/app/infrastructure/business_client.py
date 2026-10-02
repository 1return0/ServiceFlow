from __future__ import annotations

import time
from collections.abc import Callable

import httpx
from pydantic import BaseModel, Field, ValidationError
from uuid import UUID

from app.infrastructure.retry_policy import BoundedRetryPolicy


class BusinessServiceHealth(BaseModel):
    status: str
    service: str
    version: str


class BusinessServiceUnavailableError(RuntimeError):
    """The Java business service could not satisfy its health contract."""


class BusinessServiceResponseError(RuntimeError):
    """The Java service understood the request but rejected its business result."""

    def __init__(self, status_code: int) -> None:
        super().__init__("business service rejected the request")
        self.status_code = status_code


class BusinessTicket(BaseModel):
    id: UUID
    requester_reference: str = Field(validation_alias="requesterReference")
    category: str
    summary: str
    submitted_at: str = Field(validation_alias="submittedAt")
    status: str
    version: int


class BusinessNotificationSummary(BaseModel):
    unread_count: int = Field(validation_alias="unreadCount", ge=0)


class BusinessAuthenticatedSubject(BaseModel):
    """Trusted identity returned by Java after it verifies the forwarded JWT."""

    subject: str = Field(min_length=1)
    roles: tuple[str, ...] = Field(min_length=1)


class BusinessHumanHandoffTask(BaseModel):
    id: UUID
    request_id: UUID = Field(validation_alias="requestId")
    handoff_reason: str = Field(validation_alias="handoffReason")
    status: str


class BusinessServiceClient:
    """Typed HTTP boundary from the Python Agent service to the Java service."""

    def __init__(
        self,
        base_url: str,
        http_client: httpx.Client,
        *,
        retry_policy: BoundedRetryPolicy | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client
        self._retry_policy = retry_policy or BoundedRetryPolicy()
        self._sleeper = sleeper

    def get_health(self) -> BusinessServiceHealth:
        try:
            response = self._http_client.get(f"{self._base_url}/api/v1/health")
            response.raise_for_status()
            return BusinessServiceHealth.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise BusinessServiceUnavailableError(
                "business service health contract is unavailable"
            ) from error

    def get_ticket(
        self,
        ticket_id: UUID,
        *,
        authorization: str,
    ) -> BusinessTicket:
        response = self._read_ticket_with_retry(ticket_id, authorization=authorization)
        try:
            payload = response.json()
            if payload.get("code") != 0:
                raise ValueError("business response code must be zero")
            return BusinessTicket.model_validate(payload["data"])
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            raise BusinessServiceUnavailableError(
                "business ticket contract is invalid"
            ) from error

    def get_notification_summary(
        self,
        *,
        authorization: str,
    ) -> BusinessNotificationSummary:
        response = self._read_notification_summary_with_retry(authorization=authorization)
        try:
            payload = response.json()
            if payload.get("code") != 0:
                raise ValueError("business response code must be zero")
            return BusinessNotificationSummary.model_validate(payload["data"])
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            raise BusinessServiceUnavailableError(
                "business notification summary contract is invalid"
            ) from error

    def get_authenticated_subject(
        self,
        *,
        authorization: str,
    ) -> BusinessAuthenticatedSubject:
        response = self._read_authenticated_subject_with_retry(
            authorization=authorization,
        )
        try:
            payload = response.json()
            if payload.get("code") != 0:
                raise ValueError("business response code must be zero")
            return BusinessAuthenticatedSubject.model_validate(payload["data"])
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            raise BusinessServiceUnavailableError(
                "business identity contract is invalid"
            ) from error

    def create_handoff_task(
        self,
        *,
        request_id: UUID,
        handoff_reason: str,
        authorization: str,
    ) -> BusinessHumanHandoffTask:
        """A write is sent once; request_id is the server-side idempotency key."""
        try:
            response = self._http_client.post(
                f"{self._base_url}/api/v1/handoffs",
                headers={"Authorization": authorization},
                json={"requestId": str(request_id), "handoffReason": handoff_reason},
            )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise BusinessServiceUnavailableError("business handoff API is unavailable") from error
        if response.status_code >= 400:
            raise BusinessServiceResponseError(response.status_code)
        try:
            payload = response.json()
            if payload.get("code") != 0:
                raise ValueError("business response code must be zero")
            return BusinessHumanHandoffTask.model_validate(payload["data"])
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            raise BusinessServiceUnavailableError("business handoff contract is invalid") from error

    def _read_notification_summary_with_retry(
        self,
        *,
        authorization: str,
    ) -> httpx.Response:
        for attempt_number in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = self._http_client.get(
                    f"{self._base_url}/api/v1/notifications/me/summary",
                    headers={"Authorization": authorization},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                if attempt_number == self._retry_policy.max_attempts:
                    raise BusinessServiceUnavailableError(
                        "business notification API is unavailable"
                    ) from error
                self._wait_before_retry(attempt_number)
                continue
            if self._is_retryable_status(response.status_code):
                if attempt_number == self._retry_policy.max_attempts:
                    raise BusinessServiceResponseError(response.status_code)
                self._wait_before_retry(attempt_number)
                continue
            if response.status_code >= 400:
                raise BusinessServiceResponseError(response.status_code)
            return response
        raise AssertionError("retry loop must return or raise")

    def _read_authenticated_subject_with_retry(
        self,
        *,
        authorization: str,
    ) -> httpx.Response:
        for attempt_number in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = self._http_client.get(
                    f"{self._base_url}/api/v1/auth/me",
                    headers={"Authorization": authorization},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                if attempt_number == self._retry_policy.max_attempts:
                    raise BusinessServiceUnavailableError(
                        "business identity API is unavailable"
                    ) from error
                self._wait_before_retry(attempt_number)
                continue
            if self._is_retryable_status(response.status_code):
                if attempt_number == self._retry_policy.max_attempts:
                    raise BusinessServiceResponseError(response.status_code)
                self._wait_before_retry(attempt_number)
                continue
            if response.status_code >= 400:
                raise BusinessServiceResponseError(response.status_code)
            return response
        raise AssertionError("retry loop must return or raise")

    def _read_ticket_with_retry(
        self,
        ticket_id: UUID,
        *,
        authorization: str,
    ) -> httpx.Response:
        for attempt_number in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = self._http_client.get(
                    f"{self._base_url}/api/v1/tickets/{ticket_id}",
                    headers={"Authorization": authorization},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                if attempt_number == self._retry_policy.max_attempts:
                    raise BusinessServiceUnavailableError(
                        "business ticket API is unavailable"
                    ) from error
                self._wait_before_retry(attempt_number)
                continue

            if self._is_retryable_status(response.status_code):
                if attempt_number == self._retry_policy.max_attempts:
                    raise BusinessServiceResponseError(response.status_code)
                self._wait_before_retry(attempt_number)
                continue

            if response.status_code >= 400:
                raise BusinessServiceResponseError(response.status_code)
            return response

        raise AssertionError("retry loop must return or raise")

    def _wait_before_retry(self, completed_attempts: int) -> None:
        self._sleeper(self._retry_policy.delay_before_retry(completed_attempts))

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code in {502, 503, 504}
