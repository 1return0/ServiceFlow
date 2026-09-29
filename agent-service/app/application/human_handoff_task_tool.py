from __future__ import annotations

from uuid import UUID

from app.infrastructure.business_client import BusinessHumanHandoffTask, BusinessServiceClient


class HumanHandoffTaskTool:
    """Bounded write tool: creates an auditable Java-side task, never resolves it."""

    name = "create_human_handoff_task"

    def __init__(self, business_service_client: BusinessServiceClient) -> None:
        self._business_service_client = business_service_client

    def execute(self, *, request_id: UUID, handoff_reason: str, authorization: str) -> BusinessHumanHandoffTask:
        return self._business_service_client.create_handoff_task(
            request_id=request_id,
            handoff_reason=handoff_reason,
            authorization=authorization,
        )
