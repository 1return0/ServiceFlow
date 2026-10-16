from __future__ import annotations

from typing import Annotated, Any, Callable, Literal, TypeVar
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from typing_extensions import NotRequired, TypedDict

from app.application.retrieval.support_knowledge_answering import SupportKnowledgeAnswer
from app.application.agent.coordinator_trace import CoordinatorTrace, CoordinatorTraceRecorder
from app.application.agent.agent_harness import (
    AgentHarness,
    AgentHarnessSnapshot,
    bind_agent_harness,
)
from app.application.tools.human_handoff_task_tool import HumanHandoffTaskTool
from app.application.agent.handoff_guard import CampusRiskHandoffGuard, HandoffGuard
from app.application.agent.knowledge_specialist_agent import (
    KnowledgeSpecialist,
    TicketKnowledgeContext,
)
from app.application.agent.ticket_specialist_agent import (
    TicketAuthorizationRequiredError,
    TicketSpecialist,
)
from app.application.agent.notification_specialist_agent import NotificationSpecialist
from app.domain.triage_plan import HandoffReason, TriagePlan, TriagePlanner
from app.infrastructure.clients.business_client import BusinessNotificationSummary, BusinessTicket
from app.application.memory.safe_conversation import (
    merge_safe_conversation_turns,
    safe_agent_summary,
    safe_conversation_turn,
)


T = TypeVar("T")


def _merge_conversation_turns(
    existing: list[dict[str, str] | str],
    incoming: list[dict[str, str] | str],
) -> list[dict[str, str]]:
    return merge_safe_conversation_turns(existing, incoming)


class CampusSupportTriageState(TypedDict):
    user_query: str
    # Only the Runtime supplies this after Java validates the Bearer JWT.
    owner_id: NotRequired[str]
    conversation_turns: Annotated[list[dict[str, str]], _merge_conversation_turns]
    plan: NotRequired[TriagePlan]
    ticket: NotRequired[BusinessTicket]
    knowledge_answer: NotRequired[SupportKnowledgeAnswer]
    notification_summary: NotRequired[BusinessNotificationSummary]


class CampusSupportTriageContext(TypedDict):
    """Invocation-only values. LangGraph never checkpoints this context."""

    authorization: str | None
    trace_recorder: CoordinatorTraceRecorder
    preferences: dict[str, str]
    harness: AgentHarness


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
    harness_snapshot: AgentHarnessSnapshot


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
        checkpointer: Any | None = None,
    ) -> None:
        self._planner = planner
        self._ticket_specialist = ticket_specialist
        self._knowledge_specialist = knowledge_specialist
        self._handoff_guard = handoff_guard or CampusRiskHandoffGuard()
        self._notification_specialist = notification_specialist
        self._handoff_task_tool = handoff_task_tool

        builder = StateGraph(
            CampusSupportTriageState,
            context_schema=CampusSupportTriageContext,
        )
        builder.add_node("triage", self._triage)
        builder.add_node("lookup_ticket", self._lookup_ticket)
        builder.add_node("get_notification_summary", self._get_notification_summary)
        builder.add_node("answer_support_knowledge", self._answer_support_knowledge)
        builder.add_node(
            "answer_ticket_context_knowledge",
            self._answer_ticket_context_knowledge,
        )
        builder.add_node("handoff_to_human", self._handoff_to_human)
        builder.add_node("record_assistant", self._record_assistant)
        builder.add_edge(START, "triage")
        builder.add_conditional_edges(
            "triage",
            self._route_after_triage,
            {
                "lookup_ticket": "lookup_ticket",
                "get_notification_summary": "get_notification_summary",
                "answer_support_knowledge": "answer_support_knowledge",
                "handoff_to_human": "handoff_to_human",
                "refuse": "record_assistant",
            },
        )
        builder.add_conditional_edges(
            "lookup_ticket",
            self._route_after_ticket_lookup,
            {
                "answer_ticket_context_knowledge": (
                    "answer_ticket_context_knowledge"
                ),
                "end": "record_assistant",
            },
        )
        builder.add_edge("answer_support_knowledge", "record_assistant")
        builder.add_edge("get_notification_summary", "record_assistant")
        builder.add_edge("answer_ticket_context_knowledge", "record_assistant")
        builder.add_edge("handoff_to_human", "record_assistant")
        builder.add_edge("record_assistant", END)
        self._graph = builder.compile(checkpointer=checkpointer)
        # Public knowledge requests have no verified owner and therefore no
        # thread_id. They must stay stateless rather than failing Checkpointer
        # validation or borrowing another user's conversation.
        self._stateless_graph = (
            builder.compile() if checkpointer is not None else self._graph
        )

    def invoke(
        self,
        *,
        user_query: str,
        authorization: str | None = None,
        owner_id: str | None = None,
        thread_id: str | None = None,
        preferences: dict[str, str] | None = None,
    ) -> CampusSupportTriageResult:
        recorder = CoordinatorTraceRecorder()
        harness = AgentHarness()
        initial_state: CampusSupportTriageState = {
            "user_query": user_query,
            "authorization": authorization,
        }
        if owner_id is not None:
            initial_state["owner_id"] = owner_id
        config = {"configurable": {}}
        if thread_id is not None:
            config["configurable"]["thread_id"] = thread_id
        active_graph = (
            self._graph if thread_id is not None else self._stateless_graph
        )
        state = active_graph.invoke(
            initial_state,
            config=config,
            context={
                "authorization": authorization,
                "trace_recorder": recorder,
                "preferences": preferences or {},
                "harness": harness,
            },
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
            "harness_snapshot": harness.snapshot(),
        }

    def get_conversation_turns(self, *, thread_id: str) -> tuple[dict[str, str], ...]:
        if getattr(self._graph, "checkpointer", None) is None:
            raise RuntimeError("triage conversation memory is not prepared")
        snapshot = self._graph.get_state(
            {"configurable": {"thread_id": thread_id}}
        )
        values = getattr(snapshot, "values", {}) if snapshot is not None else {}
        turns = values.get("conversation_turns", ())
        return tuple(
            turn for turn in turns
            if isinstance(turn, dict)
            and isinstance(turn.get("role"), str)
            and isinstance(turn.get("content"), str)
        )

    def clear_conversation_thread(self, *, thread_id: str) -> bool:
        checkpointer = getattr(self._graph, "checkpointer", None)
        delete_thread = getattr(checkpointer, "delete_thread", None)
        if not callable(delete_thread):
            raise RuntimeError("triage conversation memory is not prepared")
        snapshot = self._graph.get_state(
            {"configurable": {"thread_id": thread_id}}
        )
        if not getattr(snapshot, "values", None):
            return False
        delete_thread(thread_id)
        return True

    def _triage(
        self,
        state: CampusSupportTriageState,
        runtime: Runtime[CampusSupportTriageContext],
    ) -> dict[str, TriagePlan]:
        def plan() -> TriagePlan:
            handoff_reason = self._handoff_guard.detect(user_query=state["user_query"])
            if handoff_reason is not None:
                return TriagePlan(
                    decision="handoff_to_human",
                    reason="high-risk campus support issue requires human handling",
                    handoff_reason=handoff_reason,
                )
            with bind_agent_harness(_harness(runtime)):
                return self._planner.plan(
                    user_query=_planner_query(
                        tuple(state.get("conversation_turns", ())),
                        state["user_query"],
                        preferences=runtime.context["preferences"],
                    )
                )

        recorder = _trace_recorder(runtime)
        selected_plan = recorder.capture(
            node="triage",
            specialist_identity="campus-support-coordinator-v1",
            tool_name="triage_planner",
            operation=plan,
        )
        recorder.record_route(selected_plan.decision)
        result: dict[str, object] = {
            "plan": selected_plan,
        }
        if state["user_query"].strip():
            result["conversation_turns"] = [
                safe_conversation_turn(
                    role="user", content=state["user_query"]
                ).to_checkpoint()
            ]
        return result

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
        runtime: Runtime[CampusSupportTriageContext],
    ) -> dict[str, BusinessNotificationSummary]:
        if self._notification_specialist is None:
            raise RuntimeError("notification specialist is not configured")
        return {"notification_summary": _trace_recorder(runtime).capture(
            node="get_notification_summary",
            specialist_identity=self._notification_specialist.identity,
            tool_name="notification_summary",
            operation=lambda: _harness(runtime).invoke_tool(
                "notification_summary",
                lambda: self._notification_specialist.summarize(
                    authorization=runtime.context["authorization"]
                ),
            ),
        )}

    def _lookup_ticket(
        self,
        state: CampusSupportTriageState,
        runtime: Runtime[CampusSupportTriageContext],
    ) -> dict[str, BusinessTicket]:
        ticket_id = state["plan"].ticket_id
        if ticket_id is None:
            raise ValueError("lookup_ticket plan must contain ticket_id")
        return {"ticket": _trace_recorder(runtime).capture(
            node="lookup_ticket",
            specialist_identity=self._ticket_specialist.identity,
            tool_name="ticket_lookup",
            operation=lambda: _harness(runtime).invoke_tool(
                "ticket_lookup",
                lambda: self._ticket_specialist.lookup(
                    ticket_id=ticket_id,
                    authorization=runtime.context["authorization"],
                ),
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
        runtime: Runtime[CampusSupportTriageContext],
    ) -> dict[str, SupportKnowledgeAnswer]:
        return {"knowledge_answer": _trace_recorder(runtime).capture(
            node="answer_support_knowledge",
            specialist_identity=self._knowledge_specialist.identity,
            tool_name="support_knowledge_answer",
            operation=lambda: _harness(runtime).invoke_tool(
                "support_knowledge_answer",
                lambda: _invoke_with_bound_harness(
                    runtime,
                    lambda: self._knowledge_specialist.answer(
                        user_query=state["plan"].knowledge_question or state["user_query"],
                    ),
                ),
            ),
        )}

    def _answer_ticket_context_knowledge(
        self,
        state: CampusSupportTriageState,
        runtime: Runtime[CampusSupportTriageContext],
    ) -> dict[str, SupportKnowledgeAnswer]:
        ticket = state["ticket"]
        return {"knowledge_answer": _trace_recorder(runtime).capture(
            node="answer_ticket_context_knowledge",
            specialist_identity=self._knowledge_specialist.identity,
            tool_name="support_knowledge_answer",
            operation=lambda: _harness(runtime).invoke_tool(
                "support_knowledge_answer",
                lambda: _invoke_with_bound_harness(
                    runtime,
                    lambda: self._knowledge_specialist.answer(
                        user_query=state["user_query"],
                        ticket_context=TicketKnowledgeContext(
                            category=ticket.category,
                            status=ticket.status,
                        ),
                    ),
                ),
            ),
        )}

    def _handoff_to_human(
        self,
        state: CampusSupportTriageState,
        runtime: Runtime[CampusSupportTriageContext],
    ) -> dict[str, object]:
        """Explicit safety boundary; real human notification is added later."""
        recorder = _trace_recorder(runtime)
        recorder.capture(
            node="handoff_to_human",
            specialist_identity="campus-risk-handoff-guard-v1",
            tool_name=None,
            operation=lambda: None,
        )
        if self._handoff_task_tool is not None and runtime.context["authorization"] is not None:
            recorder.capture(
                node="create_human_handoff_task",
                specialist_identity="campus-risk-handoff-guard-v1",
                tool_name=self._handoff_task_tool.name,
                operation=lambda: _harness(runtime).invoke_tool(
                    "create_human_handoff_task",
                    lambda: self._handoff_task_tool.invoke(
                        {"handoff_reason": state["plan"].handoff_reason or ""},
                        request_id=UUID(recorder.request_id),
                        authorization=runtime.context["authorization"] or "",
                    ),
                ),
            )
        return {}

    def _record_assistant(
        self,
        state: CampusSupportTriageState,
    ) -> dict[str, object]:
        plan = state["plan"]
        outcome, reason = _safe_final_outcome(state, plan)
        return {"conversation_turns": [
            safe_agent_summary(
                outcome=outcome,
                reason=reason,
            ).to_checkpoint()
        ]}


def _trace_recorder(
    runtime: Runtime[CampusSupportTriageContext],
) -> CoordinatorTraceRecorder:
    recorder = runtime.context.get("trace_recorder")
    if not isinstance(recorder, CoordinatorTraceRecorder):
        raise RuntimeError("triage trace recorder is required at invocation")
    return recorder


def _harness(runtime: Runtime[CampusSupportTriageContext]) -> AgentHarness:
    harness = runtime.context.get("harness")
    if not isinstance(harness, AgentHarness):
        raise RuntimeError("triage agent harness is required at invocation")
    return harness


def _invoke_with_bound_harness(
    runtime: Runtime[CampusSupportTriageContext],
    operation: Callable[[], T],
) -> T:
    """Lets nested model adapters charge their request-scoped model budget."""

    with bind_agent_harness(_harness(runtime)):
        return operation()


def _planner_query(
    history: tuple[dict[str, str], ...],
    current_query: str,
    *,
    preferences: dict[str, str] | None = None,
) -> str:
    sections: list[str] = []
    if preferences:
        sections.append(
            "Consented user preferences (use only when relevant; "
            "the current request takes priority):\n"
            + "\n".join(
                f"- {key}: {value}"
                for key, value in sorted(preferences.items())
            )
        )
    previous = "\n".join(
        f"- {turn['role']}: {turn['content']}" for turn in history
    )
    if previous:
        sections.append(
            "Previous user turns (context only; obey current request):\n"
            f"{previous}"
        )
    if not sections:
        return current_query
    sections.append(f"Current user request:\n{current_query}")
    return "\n\n".join(sections)


def _safe_final_outcome(
    state: CampusSupportTriageState,
    plan: TriagePlan,
) -> tuple[str, str]:
    """Describe the completed branch without storing business payloads."""
    if state.get("knowledge_answer") is not None:
        return (
            state["knowledge_answer"].status,
            "campus support knowledge guidance was completed",
        )
    if state.get("notification_summary") is not None:
        return (
            "notification_summary",
            "notification summary was completed",
        )
    if state.get("ticket") is not None:
        return ("ticket_lookup", "ticket lookup was completed")
    if plan.decision == "handoff_to_human":
        return ("handoff_to_human", "human handoff guidance was created")
    return (plan.decision, plan.reason)
