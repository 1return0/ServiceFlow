from __future__ import annotations

from app.infrastructure.business_client import (
    BusinessNotificationSummary,
    BusinessServiceClient,
)


class NotificationSummaryTool:
    """Reads only the authenticated student's compact notification state."""

    name = "get_notification_summary"

    def __init__(self, business_service_client: BusinessServiceClient) -> None:
        self._business_service_client = business_service_client

    def execute(self, *, authorization: str) -> BusinessNotificationSummary:
        return self._business_service_client.get_notification_summary(
            authorization=authorization
        )
