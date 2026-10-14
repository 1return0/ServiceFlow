from __future__ import annotations

from typing import Protocol

from app.application.notification_summary_tool import NotificationSummaryTool
from app.application.ticket_specialist_agent import TicketAuthorizationRequiredError
from app.infrastructure.business_client import BusinessNotificationSummary


class NotificationSpecialist(Protocol):
    def summarize(self, *, authorization: str | None) -> BusinessNotificationSummary:
        ...


class NotificationSpecialistAgent:
    """Specialist worker for a student's private notification summary."""

    identity = "notification-specialist-agent-v1"

    def __init__(self, notification_summary_tool: NotificationSummaryTool) -> None:
        self._notification_summary_tool = notification_summary_tool

    def summarize(self, *, authorization: str | None) -> BusinessNotificationSummary:
        if authorization is None or not authorization.strip():
            raise TicketAuthorizationRequiredError(
                "notification summary requires an authorization header"
            )
        return self._notification_summary_tool.invoke({}, authorization=authorization)
