from __future__ import annotations

from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.domain.triage_plan import HandoffReason

from app.infrastructure.clients.business_client import BusinessHumanHandoffTask, BusinessServiceClient


class HumanHandoffTaskArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handoff_reason: HandoffReason = Field(description="Recognized account-security or physical-safety risk requiring human support.")


class HumanHandoffTaskTool:
    """Bounded write tool: creates an auditable Java-side task, never resolves it."""

    name = "create_human_handoff_task"
    description = "Route immediate account-security or physical-safety risk to human support. The runtime creates a task only with trusted authentication; otherwise it returns handoff guidance."
    arguments_model = HumanHandoffTaskArguments
    routing_decision = "handoff_to_human"

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return self.arguments_model.model_json_schema()

    def invoke(self, raw_arguments: dict[str, Any], *, request_id: UUID,
               authorization: str) -> BusinessHumanHandoffTask:
        arguments = self.arguments_model.model_validate(raw_arguments)
        return self.execute(request_id=request_id, handoff_reason=arguments.handoff_reason,
                            authorization=authorization)

    def __init__(self, business_service_client: BusinessServiceClient) -> None:
        self._business_service_client = business_service_client

    def execute(self, *, request_id: UUID, handoff_reason: str, authorization: str) -> BusinessHumanHandoffTask:
        arguments = self.arguments_model(handoff_reason=handoff_reason)
        return self._business_service_client.create_handoff_task(
            request_id=request_id,
            handoff_reason=arguments.handoff_reason,
            authorization=authorization,
        )
