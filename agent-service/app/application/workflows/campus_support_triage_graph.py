from __future__ import annotations

from typing import Literal
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict

from app.application.support_knowledge_answering import SupportKnowledgeAnswer
from app.application.coordinator_trace import CoordinatorTrace, CoordinatorTraceRecorder
from app.application.human_handoff_task_tool import HumanHandoffTaskTool
from app.application.handoff_guard import CampusRiskHandoffGuard, HandoffGuard
from app.application.knowledge_specialist_agent import (
    KnowledgeSpecialist,
    TicketKnowledgeContext,
)
from app.application.ticket_specialist_agent import (
    TicketAuthorizationRequiredError,
    TicketSpecialist,
)
from app.application.notification_specialist_agent import NotificationSpecialist
from app.domain.triage_plan import HandoffReason, TriagePlan, TriagePlanner
from app.infrastructure.business_client import BusinessNotificationSummary, BusinessTicket


class CampusSupportTriageState(TypedDict):
    user_query: str
    authorization: str | None
    trace_recorder: CoordinatorTraceRecorder
    plan: NotRequired[TriagePlan]
    ticket: NotRequired[BusinessTicket]
    knowledge_answer: NotRequired[SupportKnowledgeAnswer]
    notification_summary: NotRequired[BusinessNotificationSummary]


class CampusSupportTriageResult(TypedDict):
    decision: Literal[
        "lookup_ticket",
        "get_notification_summary",
        "answer_support_knowledge",
        "handoff_to_human",
        "refuse",
    ]
    reason: str
    handoff_reason: HandoffReason | None
    ticket: BusinessTicket | None
    knowledge_answer: SupportKnowledgeAnswer | None
    notification_summary: BusinessNotificationSummary | None
    trace: CoordinatorTrace


class CampusSupportTriageGraph:
    """Routes one campus-support request to exactly one bounded capability."""

    def __init__(
        self,
        planner: TriagePlanner,
        ticket_specialist: TicketSpecialist,
        knowledge_specialist: KnowledgeSpecialist,
        handoff_guard: HandoffGuard | None = None,
        notification_specialist: NotificationSpecialist | None = None,
        handoff_task_tool: HumanHandoffTaskTool | None = None,
    ) -> None:
        self._planner = planner
        self._ticket_specialist = ticket_specialist
        self._knowledge_specialist = knowledge_specialist
        self._handoff_guard = handoff_guard or CampusRiskHandoffGuard()
        self._notification_specialist = notification_specialist
        self._handoff_task_tool = handoff_task_tool

        builder = StateGraph(CampusSupportTriageState)
        builder.add_node("triage", self._triage)
        builder.add_node("lookup_ticket", self._lookup_ticket)
        builder.add_node("get_notification_summary", self._get_notification_summary)
        builder.add_node("answer_support_knowledge", self._answer_support_knowledge)
        builder.add_node(
            "answer_ticket_context_knowledge",
            self._answer_ticket_context_knowledge,
        )
        builder.add_node("handoff_to_human", self._handoff_to_human)
        builder.add_edge(START, "triage")
        builder.add_conditional_edges(
            "triage",
            self._route_after_triage,
            {
                "lookup_ticket": "lookup_ticket",
                "get_notification_summary": "get_notification_summary",
                "answer_support_knowledge": "answer_support_knowledge",
                "handoff_to_human": "handoff_to_human",
                "refuse": END,
            },
        )
        builder.add_conditional_edges(
            "lookup_ticket",
            self._route_after_ticket_lookup,
            {
                "answer_ticket_context_knowledge": (
                    "answer_ticket_context_knowledge"
                ),
                "end": END,
            },
        )
        builder.add_edge("answer_support_knowledge", END)
        builder.add_edge("get_notification_summary", END)
        builder.add_edge("answer_ticket_context_knowledge", END)
        builder.add_edge("handoff_to_human", END)
        self._graph = builder.compile()

    def invoke(
        self,
        *,
        user_query: str,
        authorization: str | None = None,
    ) -> CampusSupportTriageResult:
        recorder = CoordinatorTraceRecorder()
        state = self._graph.invoke(
            {
                "user_query": user_query,
                "authorization": authorization,
                "trace_recorder": recorder,
            }
        )
        plan = state["plan"]
        return {
            "decision": plan.decision,
            "reason": plan.reason,
            "handoff_reason": plan.handoff_reason,
            "ticket": state.get("ticket"),
            "knowledge_answer": state.get("knowledge_answer"),
            "notification_summary": state.get("notification_summary"),
            "trace": recorder.snapshot(),
        }

    def _triage(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, TriagePlan]:
        def plan() -> TriagePlan:
            handoff_reason = self._handoff_guard.detect(user_query=state["user_query"])
            if handoff_reason is not None:
                return TriagePlan(
                    decision="handoff_to_human",
                    reason="high-risk campus support issue requires human handling",
                    handoff_reason=handoff_reason,
                )
            return self._planner.plan(user_query=state["user_query"])

        selected_plan = state["trace_recorder"].capture(
            node="triage",
            specialist_identity="campus-support-coordinator-v1",
            tool_name="triage_planner",
            operation=plan,
        )
        state["trace_recorder"].record_route(selected_plan.decision)
        return {"plan": selected_plan}

    def _route_after_triage(
        self,
        state: CampusSupportTriageState,
    ) -> Literal[
        "lookup_ticket",
        "get_notification_summary",
        "answer_support_knowledge",
        "handoff_to_human",
        "refuse",
    ]:
        return state["plan"].decision

    def _get_notification_summary(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, BusinessNotificationSummary]:
        if self._notification_specialist is None:
            raise RuntimeError("notification specialist is not configured")
        return {"notification_summary": state["trace_recorder"].capture(
            node="get_notification_summary",
            specialist_identity=self._notification_specialist.identity,
            tool_name="notification_summary",
            operation=lambda: self._notification_specialist.summarize(
                authorization=state["authorization"]
            ),
        )}

    def _lookup_ticket(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, BusinessTicket]:
        ticket_id = state["plan"].ticket_id
        if ticket_id is None:
            raise ValueError("lookup_ticket plan must contain ticket_id")
        return {"ticket": state["trace_recorder"].capture(
            node="lookup_ticket",
            specialist_identity=self._ticket_specialist.identity,
            tool_name="ticket_lookup",
            operation=lambda: self._ticket_specialist.lookup(
                ticket_id=ticket_id,
                authorization=state["authorization"],
            ),
        )}

    def _route_after_ticket_lookup(
        self,
        state: CampusSupportTriageState,
    ) -> Literal["answer_ticket_context_knowledge", "end"]:
        return (
            "answer_ticket_context_knowledge"
            if state["plan"].follow_up_knowledge
            else "end"
        )

    def _answer_support_knowledge(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, SupportKnowledgeAnswer]:
        return {"knowledge_answer": state["trace_recorder"].capture(
            node="answer_support_knowledge",
            specialist_identity=self._knowledge_specialist.identity,
            tool_name="support_knowledge_answer",
            operation=lambda: self._knowledge_specialist.answer(
                user_query=state["user_query"],
            ),
        )}

    def _answer_ticket_context_knowledge(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, SupportKnowledgeAnswer]:
        ticket = state["ticket"]
        return {"knowledge_answer": state["trace_recorder"].capture(
            node="answer_ticket_context_knowledge",
            specialist_identity=self._knowledge_specialist.identity,
            tool_name="support_knowledge_answer",
            operation=lambda: self._knowledge_specialist.answer(
                user_query=state["user_query"],
                ticket_context=TicketKnowledgeContext(
                    category=ticket.category,
                    status=ticket.status,
                ),
            ),
        )}

    def _handoff_to_human(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, object]:
        """Explicit safety boundary; real human notification is added later."""
        state["trace_recorder"].capture(
            node="handoff_to_human",
            specialist_identity="campus-risk-handoff-guard-v1",
            tool_name=None,
            operation=lambda: None,
        )
        if self._handoff_task_tool is not None and state["authorization"] is not None:
            state["trace_recorder"].capture(
                node="create_human_handoff_task",
                specialist_identity="campus-risk-handoff-guard-v1",
                tool_name=self._handoff_task_tool.name,
                operation=lambda: self._handoff_task_tool.execute(
                    request_id=UUID(state["trace_recorder"].request_id),
                    handoff_reason=state["plan"].handoff_reason or "",
                    authorization=state["authorization"] or "",
                ),
            )
        return {}
