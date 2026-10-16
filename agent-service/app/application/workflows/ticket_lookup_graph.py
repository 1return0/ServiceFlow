from __future__ import annotations

from uuid import UUID

from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict

from app.infrastructure.clients.business_client import BusinessTicket
from app.application.tools.ticket_lookup_tool import TicketLookupTool


class TicketLookupState(TypedDict):
    ticket_id: UUID
    authorization: str
    ticket: NotRequired[BusinessTicket]


class TicketLookupGraph:
    """Smallest executable LangGraph baseline: one state, one tool node, one end."""

    def __init__(self, ticket_lookup_tool: TicketLookupTool) -> None:
        self._ticket_lookup_tool = ticket_lookup_tool
        builder = StateGraph(TicketLookupState)
        builder.add_node("lookup_ticket", self._lookup_ticket)
        builder.add_edge(START, "lookup_ticket")
        builder.add_edge("lookup_ticket", END)
        self._graph = builder.compile()

    def invoke(self, *, ticket_id: UUID, authorization: str) -> BusinessTicket:
        state = self._graph.invoke(
            {
                "ticket_id": ticket_id,
                "authorization": authorization,
            }
        )
        return state["ticket"]

    def _lookup_ticket(self, state: TicketLookupState) -> dict[str, BusinessTicket]:
        return {
            "ticket": self._ticket_lookup_tool.execute(
                ticket_id=state["ticket_id"],
                authorization=state["authorization"],
            )
        }
