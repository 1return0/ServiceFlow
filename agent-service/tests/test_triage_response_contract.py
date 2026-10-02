from unittest import TestCase
from uuid import UUID

from pydantic import ValidationError

from app.api.routes import (
    AgentHarnessResponse,
    CampusSupportTriageResponse,
    CoordinatorTraceResponse,
    CoordinatorTraceStepResponse,
    HandoffGuidanceResponse,
    SupportKnowledgeAnswerResponse,
)
from app.infrastructure.business_client import BusinessTicket


class CampusSupportTriageResponseContractTest(TestCase):
    def test_rejects_a_ticket_decision_without_a_ticket_payload(self) -> None:
        with self.assertRaises(ValidationError):
            CampusSupportTriageResponse(
                decision="lookup_ticket",
                reason="ticket found",
                handoff_reason=None,
                handoff_guidance=None,
                ticket=None,
                knowledge_answer=None,
            )

    def test_rejects_a_handoff_that_contains_a_knowledge_payload(self) -> None:
        with self.assertRaises(ValidationError):
            CampusSupportTriageResponse(
                decision="handoff_to_human",
                reason="smoke",
                handoff_reason="physical_safety_risk",
                handoff_guidance=HandoffGuidanceResponse(
                    reason="physical_safety_risk",
                    title="Stop using the equipment",
                    message="Manual handling is required.",
                    immediate_actions=["Stop using the equipment."],
                ),
                ticket=None,
                knowledge_answer=SupportKnowledgeAnswerResponse(
                    status="answered",
                    answer_text="incorrect mixed payload",
                    citations=[],
                    model_called=False,
                    model_identity=None,
                ),
            )

    def test_accepts_a_ticket_only_response(self) -> None:
        response = CampusSupportTriageResponse(
            decision="lookup_ticket",
            reason="ticket found",
            handoff_reason=None,
            handoff_guidance=None,
            ticket=BusinessTicket(
                id=UUID("009e3cce-8f4d-448d-a060-6ce2624eac77"),
                requesterReference="student-001",
                category="CAMPUS_NETWORK",
                summary="network issue",
                submittedAt="2026-09-07T09:00:00Z",
                status="SUBMITTED",
                version=0,
            ),
            knowledge_answer=None,
            trace=_trace(),
            harness=AgentHarnessResponse(
                model_call_count=0,
                tool_call_count=1,
                elapsed_seconds=0.0,
                steps=[],
            ),
        )

        self.assertEqual("lookup_ticket", response.decision)
        self.assertIsNotNone(response.ticket)


def _trace() -> CoordinatorTraceResponse:
    return CoordinatorTraceResponse(
        request_id="trace-test",
        steps=[
            CoordinatorTraceStepResponse(
                node="triage",
                specialist_identity="coordinator",
                tool_name="triage_planner",
                elapsed_seconds=0.0,
                status="succeeded",
                decision=None,
                failure_code=None,
            )
        ],
    )


if __name__ == "__main__":
    import unittest

    unittest.main()
