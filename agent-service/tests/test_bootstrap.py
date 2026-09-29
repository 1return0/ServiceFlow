from __future__ import annotations

from pathlib import Path
from uuid import UUID
from unittest import TestCase

import httpx

from app.application.model_ticket_lookup_planner import ModelTicketLookupPlanner
from app.application.fallback_triage_planner import FallbackTriagePlanner
from app.bootstrap import (
    build_business_service_client,
    build_support_knowledge_document_parsing_service,
    build_ticket_lookup_planner,
    build_triage_planner,
)
from app.config import Settings
from app.domain.ticket_lookup_plan import RuleBasedTicketLookupPlanner
from app.domain.triage_plan import RuleBasedTriagePlanner


class PlannerBootstrapTest(TestCase):
    def test_builds_a_client_using_the_configured_read_retry_budget(self) -> None:
        ticket_id = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ReadTimeout("temporary", request=request)
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "id": str(ticket_id),
                        "requesterReference": "student-001",
                        "category": "CAMPUS_NETWORK",
                        "summary": "Network access issue",
                        "submittedAt": "2026-09-08T00:00:00Z",
                        "status": "IN_PROGRESS",
                        "version": 1,
                    },
                },
                request=request,
            )

        settings = Settings(
            business_service_read_max_attempts=3,
            business_service_read_initial_backoff_seconds=0.0,
        )
        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            ticket = build_business_service_client(
                settings,
                http_client,
            ).get_ticket(ticket_id, authorization="Bearer test-token")

        self.assertEqual(ticket_id, ticket.id)
        self.assertEqual(3, call_count)

    def test_uses_rule_based_planner_when_model_is_disabled(self) -> None:
        planner = build_ticket_lookup_planner(Settings())

        self.assertIsInstance(planner, RuleBasedTicketLookupPlanner)

    def test_builds_model_planner_when_enabled_and_configured(self) -> None:
        planner = build_ticket_lookup_planner(
            Settings(
                planner_model_enabled=True,
                planner_model_base_url="https://example.invalid/v1",
                planner_model_api_key="test-only-key",
                planner_model_name="qwen-test",
            )
        )

        self.assertIsInstance(planner, ModelTicketLookupPlanner)

    def test_rejects_enabled_model_without_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API_KEY"):
            build_ticket_lookup_planner(
                Settings(
                    planner_model_enabled=True,
                    planner_model_base_url="https://example.invalid/v1",
                )
            )

    def test_uses_rule_based_triage_when_triage_model_is_disabled(self) -> None:
        planner = build_triage_planner(Settings())

        self.assertIsInstance(planner, RuleBasedTriagePlanner)

    def test_builds_model_triage_when_enabled_and_configured(self) -> None:
        planner = build_triage_planner(
            Settings(
                triage_model_enabled=True,
                planner_model_base_url="https://example.invalid/v1",
                planner_model_api_key="test-only-key",
                planner_model_name="qwen-test",
            )
        )

        self.assertIsInstance(planner, FallbackTriagePlanner)

    def test_rejects_enabled_triage_model_without_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API_KEY"):
            build_triage_planner(
                Settings(
                    triage_model_enabled=True,
                    planner_model_base_url="https://example.invalid/v1",
                )
            )

    def test_rejects_enabled_ocr_without_its_required_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "OCR_MODEL_BASE_URL"):
            build_support_knowledge_document_parsing_service(
                Path("."),
                Settings(ocr_enabled=True),
            )
