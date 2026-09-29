import unittest
from uuid import UUID

from app.application.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeCitation,
)
from app.application.knowledge_specialist_agent import TicketKnowledgeContext
from app.application.workflows.campus_support_triage_graph import (
    CampusSupportTriageGraph,
)
from app.domain.triage_plan import TriagePlan
from app.infrastructure.business_client import BusinessTicket


TICKET_ID = UUID("009e3cce-8f4d-448d-a060-6ce2624eac77")


class FixedPlanner:
    def __init__(self, plan: TriagePlan) -> None:
        self._plan = plan

    def plan(self, *, user_query: str) -> TriagePlan:
        return self._plan


class RecordingHandoffGuard:
    identity = "recording-handoff-guard"

    def __init__(self, reason: str | None = None) -> None:
        self._reason = reason
        self.queries: list[str] = []

    def detect(self, *, user_query: str) -> str | None:
        self.queries.append(user_query)
        return self._reason


class RecordingTicketSpecialist:
    identity = "recording-ticket-specialist"

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    def lookup(
        self,
        *,
        ticket_id: UUID,
        authorization: str | None,
    ) -> BusinessTicket:
        assert authorization is not None
        self.calls.append((ticket_id, authorization))
        return BusinessTicket(
            id=ticket_id,
            requesterReference="student-001",
            category="campus_network",
            summary="campus network issue",
            status="SUBMITTED",
            submittedAt="2026-09-07T09:00:00Z",
            version=0,
        )


class RecordingKnowledgeSpecialist:
    identity = "recording-knowledge-specialist"

    def __init__(self) -> None:
        self.questions: list[str] = []
        self.ticket_contexts: list[TicketKnowledgeContext | None] = []

    def answer(
        self,
        *,
        user_query: str,
        ticket_context: TicketKnowledgeContext | None = None,
    ) -> SupportKnowledgeAnswer:
        self.questions.append(user_query)
        self.ticket_contexts.append(ticket_context)
        return SupportKnowledgeAnswer(
            status="answered",
            answer_text="Please reset the campus network password first.",
            citations=(
                SupportKnowledgeCitation(
                    article_id="network-password-reset",
                    title="Campus network account",
                    source_reference="demo://network-password-reset",
                ),
            ),
        )


class RecordingHandoffTaskTool:
    name = "create_human_handoff_task"

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str, str]] = []

    def execute(
        self,
        *,
        request_id: UUID,
        handoff_reason: str,
        authorization: str,
    ) -> None:
        self.calls.append((request_id, handoff_reason, authorization))


class CampusSupportTriageGraphTest(unittest.TestCase):
    def _build_graph(self, plan: TriagePlan, handoff_reason: str | None = None):
        self.ticket_tool = RecordingTicketSpecialist()
        self.knowledge_tool = RecordingKnowledgeSpecialist()
        self.handoff_guard = RecordingHandoffGuard(handoff_reason)
        return CampusSupportTriageGraph(
            FixedPlanner(plan),
            self.ticket_tool,
            self.knowledge_tool,
            self.handoff_guard,
        )

    def test_routes_ticket_lookup_to_ticket_tool_only(self) -> None:
        graph = self._build_graph(
            TriagePlan(
                decision="lookup_ticket",
                reason="ticket id found",
                ticket_id=TICKET_ID,
            )
        )

        result = graph.invoke(
            user_query=f"查询工单 {TICKET_ID}",
            authorization="Bearer student-token",
        )

        self.assertEqual("lookup_ticket", result["decision"])
        self.assertIsNotNone(result["ticket"])
        self.assertIsNone(result["knowledge_answer"])
        self.assertEqual([(TICKET_ID, "Bearer student-token")], self.ticket_tool.calls)
        self.assertEqual([], self.knowledge_tool.questions)
        self.assertEqual(
            ("triage", "route_after_triage", "lookup_ticket"),
            tuple(step.node for step in result["trace"].steps),
        )
        self.assertNotIn("student-token", repr(result["trace"]))

    def test_routes_a_knowledge_question_to_knowledge_tool_only(self) -> None:
        graph = self._build_graph(
            TriagePlan(
                decision="answer_support_knowledge",
                reason="public support question",
            )
        )

        result = graph.invoke(user_query="校园网连接失败怎么办？")

        self.assertEqual("answer_support_knowledge", result["decision"])
        self.assertIsNone(result["ticket"])
        self.assertEqual("answered", result["knowledge_answer"].status)
        self.assertEqual([], self.ticket_tool.calls)
        self.assertEqual(["校园网连接失败怎么办？"], self.knowledge_tool.questions)

    def test_refuse_ends_without_calling_any_tool(self) -> None:
        graph = self._build_graph(
            TriagePlan(decision="refuse", reason="blank question")
        )

        result = graph.invoke(user_query="   ")

        self.assertEqual("refuse", result["decision"])
        self.assertIsNone(result["ticket"])
        self.assertIsNone(result["knowledge_answer"])
        self.assertEqual([], self.ticket_tool.calls)
        self.assertEqual([], self.knowledge_tool.questions)

    def test_handoff_ends_without_calling_any_tool(self) -> None:
        graph = self._build_graph(
            TriagePlan(
                decision="handoff_to_human",
                reason="physical safety issue",
                handoff_reason="physical_safety_risk",
            )
        )

        result = graph.invoke(user_query="教室投影仪冒烟怎么办？")

        self.assertEqual("handoff_to_human", result["decision"])
        self.assertEqual("physical_safety_risk", result["handoff_reason"])
        self.assertIsNone(result["ticket"])
        self.assertIsNone(result["knowledge_answer"])
        self.assertEqual([], self.ticket_tool.calls)
        self.assertEqual([], self.knowledge_tool.questions)

    def test_guard_handoffs_before_the_planner_or_any_specialist(self) -> None:
        graph = self._build_graph(
            TriagePlan(
                decision="answer_support_knowledge",
                reason="planner would normally answer",
            ),
            handoff_reason="physical_safety_risk",
        )

        result = graph.invoke(user_query="机房插座冒烟了")

        self.assertEqual("handoff_to_human", result["decision"])
        self.assertEqual("physical_safety_risk", result["handoff_reason"])
        self.assertEqual([], self.ticket_tool.calls)
        self.assertEqual([], self.knowledge_tool.questions)

    def test_persists_an_authenticated_high_risk_handoff_without_leaking_the_token_to_trace(self) -> None:
        handoff_task_tool = RecordingHandoffTaskTool()
        graph = CampusSupportTriageGraph(
            FixedPlanner(TriagePlan(decision="refuse", reason="not used")),
            RecordingTicketSpecialist(),
            RecordingKnowledgeSpecialist(),
            RecordingHandoffGuard("account_security_risk"),
            handoff_task_tool=handoff_task_tool,  # type: ignore[arg-type]
        )

        result = graph.invoke(
            user_query="我的账号密码可能被泄露了",
            authorization="Bearer student-token",
        )

        self.assertEqual("handoff_to_human", result["decision"])
        self.assertEqual(1, len(handoff_task_tool.calls))
        request_id, reason, authorization = handoff_task_tool.calls[0]
        self.assertEqual(UUID(result["trace"].request_id), request_id)
        self.assertEqual("account_security_risk", reason)
        self.assertEqual("Bearer student-token", authorization)
        self.assertNotIn("student-token", repr(result["trace"]))
        self.assertEqual(
            (
                "triage",
                "route_after_triage",
                "handoff_to_human",
                "create_human_handoff_task",
            ),
            tuple(step.node for step in result["trace"].steps),
        )

    def test_composes_ticket_lookup_then_knowledge_with_minimal_context(self) -> None:
        graph = self._build_graph(
            TriagePlan(
                decision="lookup_ticket",
                reason="ticket plus next-step question",
                ticket_id=TICKET_ID,
                follow_up_knowledge=True,
            )
        )

        result = graph.invoke(
            user_query=f"工单 {TICKET_ID} 已解决但网络仍然不可用，下一步怎么处理？",
            authorization="Bearer student-token",
        )

        self.assertIsNotNone(result["ticket"])
        self.assertEqual("answered", result["knowledge_answer"].status)
        self.assertEqual(
            [TicketKnowledgeContext(category="campus_network", status="SUBMITTED")],
            self.knowledge_tool.ticket_contexts,
        )
        self.assertEqual(
            (
                "triage",
                "route_after_triage",
                "lookup_ticket",
                "answer_ticket_context_knowledge",
            ),
            tuple(step.node for step in result["trace"].steps),
        )


if __name__ == "__main__":
    unittest.main()
