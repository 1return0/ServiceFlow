from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict

from app.infrastructure.clients.business_client import BusinessTicket
from app.domain.ticket_lookup_plan import (
    TicketLookupPlan,
    TicketLookupPlanner,
)
from app.application.tools.ticket_lookup_tool import TicketLookupTool


class TicketAssistantState(TypedDict):
    user_query: str
    authorization: str
    plan: NotRequired[TicketLookupPlan]
    ticket: NotRequired[BusinessTicket]


class TicketAssistantResult(TypedDict):
    decision: Literal["lookup_ticket", "refuse"]
    reason: str
    ticket: BusinessTicket | None


class TicketAssistantGraph:
    """A planned, conditionally routed LangGraph workflow with one bounded tool."""

    def __init__(
        self,
        planner: TicketLookupPlanner,
        ticket_lookup_tool: TicketLookupTool,
    ) -> None:
        self._planner = planner
        self._ticket_lookup_tool = ticket_lookup_tool
        builder = StateGraph(TicketAssistantState)
        builder.add_node("plan", self._plan)
        builder.add_node("lookup_ticket", self._lookup_ticket)
        builder.add_edge(START, "plan")
        builder.add_conditional_edges(
            "plan",
            self._route_after_plan,
            {
                "lookup_ticket": "lookup_ticket",
                "refuse": END,
            },
        )
        builder.add_edge("lookup_ticket", END)
        self._graph = builder.compile()

    def invoke(
        self,
        *,
        user_query: str,
        authorization: str,
    ) -> TicketAssistantResult:
        state = self._graph.invoke(
            {
                "user_query": user_query,
                "authorization": authorization,
            }
        )
        plan = state["plan"]
        return {
            "decision": plan.decision,
            "reason": plan.reason,
            "ticket": state.get("ticket"),
        }

    def _plan(self, state: TicketAssistantState) -> dict[str, TicketLookupPlan]:
        return {"plan": self._planner.plan(user_query=state["user_query"])}

    def _route_after_plan(
        self,
        state: TicketAssistantState,
    ) -> Literal["lookup_ticket", "refuse"]:
        return state["plan"].decision

    def _lookup_ticket(
        self,
        state: TicketAssistantState,
    ) -> dict[str, BusinessTicket]:
        ticket_id = state["plan"].ticket_id
        if ticket_id is None:
            raise ValueError("lookup_ticket plan must contain ticket_id")
        return {
            "ticket": self._ticket_lookup_tool.execute(
                ticket_id=ticket_id,
                authorization=state["authorization"],
            )
        }
