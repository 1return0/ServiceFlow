from __future__ import annotations

import re
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, model_validator


HandoffReason = Literal["account_security_risk", "physical_safety_risk"]


class TriagePlan(BaseModel):
    """A bounded routing decision before any ticket or knowledge tool is invoked."""

    decision: Literal[
        "lookup_ticket",
        "get_notification_summary",
        "answer_support_knowledge",
        "handoff_to_human",
        "refuse",
    ]
    reason: str
    ticket_id: UUID | None = None
    handoff_reason: HandoffReason | None = None
    follow_up_knowledge: bool = False

    @model_validator(mode="after")
    def validate_arguments(self) -> "TriagePlan":
        if self.decision == "lookup_ticket" and self.ticket_id is None:
            raise ValueError("lookup_ticket decision requires ticket_id")
        if self.decision != "lookup_ticket" and self.ticket_id is not None:
            raise ValueError("only lookup_ticket decision may contain ticket_id")
        if self.decision == "handoff_to_human" and self.handoff_reason is None:
            raise ValueError("handoff_to_human decision requires handoff_reason")
        if self.decision != "handoff_to_human" and self.handoff_reason is not None:
            raise ValueError("only handoff_to_human decision may contain handoff_reason")
        if self.follow_up_knowledge and self.decision != "lookup_ticket":
            raise ValueError(
                "follow_up_knowledge is only allowed after lookup_ticket"
            )
        return self


class TriagePlanner(Protocol):
    def plan(self, *, user_query: str) -> TriagePlan:
        ...


class RuleBasedTriagePlanner:
    """Deterministic routing baseline before a model-backed triage planner is added."""

    _TICKET_ID_PATTERN = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )
    _ACCOUNT_SECURITY_SIGNALS = ("账号被盗", "账号泄露", "密码泄露")
    _PHYSICAL_SAFETY_SIGNALS = ("冒烟", "火灾", "着火", "触电", "漏电")

    @property
    def identity(self) -> str:
        return "rule-based-triage-v1"

    def plan(self, *, user_query: str) -> TriagePlan:
        normalized_query = user_query.strip()
        if not normalized_query:
            return TriagePlan(
                decision="refuse",
                reason="a non-blank campus support question is required",
            )

        handoff_reason = self._detect_handoff_reason(normalized_query)
        if handoff_reason is not None:
            return TriagePlan(
                decision="handoff_to_human",
                reason="high-risk campus support issue requires human handling",
                handoff_reason=handoff_reason,
            )

        ticket_id_match = self._TICKET_ID_PATTERN.search(normalized_query)
        if ticket_id_match is not None:
            return TriagePlan(
                decision="lookup_ticket",
                reason="a ticket_id was found in the user query",
                ticket_id=UUID(ticket_id_match.group()),
                follow_up_knowledge=self._needs_ticket_knowledge(normalized_query),
            )

        if any(
            signal in normalized_query.casefold()
            for signal in (
                "unread notification",
                "notification summary",
                "未读通知",
                "通知数量",
            )
        ):
            return TriagePlan(
                decision="get_notification_summary",
                reason="the user requested their notification summary",
            )

        return TriagePlan(
            decision="answer_support_knowledge",
            reason="no ticket_id was found, so the question is routed to public support knowledge",
        )

    def _detect_handoff_reason(self, user_query: str) -> HandoffReason | None:
        if any(signal in user_query for signal in self._ACCOUNT_SECURITY_SIGNALS):
            return "account_security_risk"
        if any(signal in user_query for signal in self._PHYSICAL_SAFETY_SIGNALS):
            return "physical_safety_risk"
        return None

    @staticmethod
    def _needs_ticket_knowledge(user_query: str) -> bool:
        return any(
            signal in user_query
            for signal in ("下一步", "如何处理", "怎么处理", "仍然", "还是")
        )
