import unittest
from uuid import UUID

import httpx

from app.infrastructure.business_client import (
    BusinessAuthenticatedSubject,
    BusinessServiceClient,
    BusinessServiceResponseError,
    BusinessServiceUnavailableError,
)
from app.infrastructure.retry_policy import BoundedRetryPolicy


def _ticket_payload(ticket_id: UUID) -> dict[str, object]:
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": str(ticket_id),
            "requesterReference": "stu-db-smoke-001",
            "category": "CAMPUS_NETWORK",
            "summary": "Database authentication smoke ticket",
            "submittedAt": "2026-08-31T00:00:00Z",
            "status": "IN_PROGRESS",
            "version": 1,
        },
    }


class BusinessServiceClientTest(unittest.TestCase):
    def test_reads_trusted_subject_only_from_java_identity_contract(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("/api/v1/auth/me", request.url.path)
            self.assertEqual(
                "Bearer verified-by-java",
                request.headers["Authorization"],
            )
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "message": "success",
                    "data": {
                        "subject": "student-001",
                        "roles": ["STUDENT"],
                    },
                },
                request=request,
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            subject = BusinessServiceClient(
                "http://business.internal",
                http_client,
            ).get_authenticated_subject(
                authorization="Bearer verified-by-java"
            )

        self.assertEqual(
            BusinessAuthenticatedSubject(
                subject="student-001",
                roles=("STUDENT",),
            ),
            subject,
        )

    def test_reads_the_java_health_contract_over_http(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "status": "UP",
                    "service": "eduops-business",
                    "version": "0.1.0",
                },
            )
        )
        with httpx.Client(transport=transport) as http_client:
            health = BusinessServiceClient(
                "http://business.internal",
                http_client,
            ).get_health()

        self.assertEqual("UP", health.status)
        self.assertEqual("eduops-business", health.service)

    def test_rejects_an_invalid_dependency_response_contract(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"status": "UP"},
            )
        )
        with httpx.Client(transport=transport) as http_client:
            client = BusinessServiceClient("http://business.internal", http_client)
            with self.assertRaises(BusinessServiceUnavailableError):
                client.get_health()

    def test_forwards_bearer_token_when_reading_a_ticket(self) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                "Bearer user-token",
                request.headers["Authorization"],
            )
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "message": "success",
                    "data": {
                        "id": str(ticket_id),
                        "requesterReference": "stu-db-smoke-001",
                        "category": "CAMPUS_NETWORK",
                        "summary": "Database authentication smoke ticket",
                        "submittedAt": "2026-08-31T00:00:00Z",
                        "status": "IN_PROGRESS",
                        "version": 1,
                    },
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            ticket = BusinessServiceClient(
                "http://business.internal",
                http_client,
            ).get_ticket(ticket_id, authorization="Bearer user-token")

        self.assertEqual(ticket_id, ticket.id)
        self.assertEqual("IN_PROGRESS", ticket.status)

    def test_retries_a_timeout_once_before_a_successful_ticket_read(self) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        request_count = 0
        sleep_delays: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            if request_count == 1:
                raise httpx.ReadTimeout("temporary timeout", request=request)
            return httpx.Response(200, json=_ticket_payload(ticket_id), request=request)

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            ticket = BusinessServiceClient(
                "http://business.internal",
                http_client,
                retry_policy=BoundedRetryPolicy(
                    max_attempts=2,
                    initial_backoff_seconds=0.25,
                ),
                sleeper=sleep_delays.append,
            ).get_ticket(ticket_id, authorization="Bearer user-token")

        self.assertEqual(2, request_count)
        self.assertEqual([0.25], sleep_delays)
        self.assertEqual(ticket_id, ticket.id)

    def test_retries_a_transient_503_once_before_a_successful_ticket_read(self) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            if request_count == 1:
                return httpx.Response(503, json={"detail": "temporary"}, request=request)
            return httpx.Response(200, json=_ticket_payload(ticket_id), request=request)

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            BusinessServiceClient(
                "http://business.internal",
                http_client,
                sleeper=lambda _: None,
            ).get_ticket(ticket_id, authorization="Bearer user-token")

        self.assertEqual(2, request_count)

    def test_does_not_retry_an_unauthorized_ticket_read(self) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(401, json={"detail": "unauthorized"}, request=request)

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            client = BusinessServiceClient(
                "http://business.internal",
                http_client,
                sleeper=lambda _: None,
            )
            with self.assertRaises(BusinessServiceResponseError) as raised:
                client.get_ticket(ticket_id, authorization="Bearer invalid-token")

        self.assertEqual(401, raised.exception.status_code)
        self.assertEqual(1, request_count)

    def test_creates_a_handoff_task_once_with_the_callers_bearer_token(self) -> None:
        request_id = UUID("b5fa40be-73b4-4849-b3b1-71a3ca3c3991")
        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            self.assertEqual("POST", request.method)
            self.assertEqual("/api/v1/handoffs", request.url.path)
            self.assertEqual("Bearer student-token", request.headers["Authorization"])
            self.assertEqual(
                {"requestId": str(request_id), "handoffReason": "account_security_risk"},
                __import__("json").loads(request.content),
            )
            return httpx.Response(
                201,
                json={
                    "code": 0,
                    "message": "success",
                    "data": {
                        "id": "b91a54ac-4111-4b3d-b799-23768b7e8784",
                        "requestId": str(request_id),
                        "handoffReason": "account_security_risk",
                        "status": "PENDING",
                    },
                },
                request=request,
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            task = BusinessServiceClient("http://business.internal", http_client).create_handoff_task(
                request_id=request_id,
                handoff_reason="account_security_risk",
                authorization="Bearer student-token",
            )

        self.assertEqual(request_id, task.request_id)
        self.assertEqual("PENDING", task.status)
        self.assertEqual(1, request_count)


if __name__ == "__main__":
    unittest.main()
