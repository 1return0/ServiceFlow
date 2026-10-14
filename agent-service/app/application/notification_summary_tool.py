from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict

from app.infrastructure.business_client import (
    BusinessNotificationSummary,
    BusinessServiceClient,
)


class NotificationSummaryArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NotificationSummaryTool:
    """Reads only the authenticated student's compact notification state."""

    name = "get_notification_summary"
    description = "Read the authenticated student's own unread count and notification summary. Takes no model-supplied identity arguments."
    arguments_model = NotificationSummaryArguments
    routing_decision = "get_notification_summary"

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return self.arguments_model.model_json_schema()

    def invoke(self, raw_arguments: dict[str, Any], *, authorization: str) -> BusinessNotificationSummary:
        self.arguments_model.model_validate(raw_arguments)
        return self.execute(authorization=authorization)

    def __init__(self, business_service_client: BusinessServiceClient) -> None:
        self._business_service_client = business_service_client

    def execute(self, *, authorization: str) -> BusinessNotificationSummary:
        return self._business_service_client.get_notification_summary(
            authorization=authorization
        )
