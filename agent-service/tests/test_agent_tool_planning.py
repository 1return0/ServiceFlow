from __future__ import annotations

import json
from unittest.mock import Mock
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.application.agent_tool_planning import AgentToolRegistry, default_tool_definitions
from app.application.human_handoff_task_tool import HumanHandoffTaskTool
from app.application.model_triage_planner import ModelTriagePlanner, TriagePlannerOutputError
from app.application.notification_summary_tool import NotificationSummaryTool
from app.application.support_knowledge_tool import SupportKnowledgeAnswerTool
from app.application.ticket_lookup_tool import TicketLookupTool
from app.application.ticket_specialist_agent import TicketSpecialistAgent
from app.application.knowledge_specialist_agent import KnowledgeSpecialistAgent
from app.application.workflows.campus_support_triage_graph import CampusSupportTriageGraph
from app.application.support_knowledge_answering import SupportKnowledgeAnswer


def call(name, arguments, **options):
    return json.dumps(dict(decision="call_tool", reason="supported request", tool_name=name,
                           arguments=arguments, **options))


def test_prompt_uses_registered_descriptions_and_pydantic_schemas():
    tools = default_tool_definitions()
    payload = json.loads(AgentToolRegistry(tools).prompt_payload("campus question"))
    assert payload["user_query"] == "campus question"
    for definition, exported in zip(tools, payload["available_tools"]):
        assert exported == dict(name=definition.name, description=definition.description,
                                arguments_schema=definition.arguments_model.model_json_schema())
        assert not {"authorization", "owner_id", "request_id", "roles"} & set(
            exported["arguments_schema"]["properties"])
        assert exported["arguments_schema"]["additionalProperties"] is False


@pytest.mark.parametrize("name,args", [
    ("delete_ticket", {}),
    ("lookup_ticket", {}),
    ("lookup_ticket", {"ticket_id": "not-a-uuid"}),
    ("lookup_ticket", {"ticket_id": str(UUID(int=1)), "authorization": "forged"}),
    ("get_notification_summary", {"owner_id": "another student"}),
    ("answer_support_knowledge", {"question": " "}),
    ("answer_support_knowledge", {"question": "q", "top_k": 999}),
    ("create_human_handoff_task", {"handoff_reason": "delete-account"}),
    ("create_human_handoff_task", {"handoff_reason": "account_security_risk", "request_id": "forged"}),
])
def test_unknown_tools_and_invalid_or_sensitive_arguments_are_rejected(name, args):
    with pytest.raises(ValueError):
        AgentToolRegistry(default_tool_definitions()).decode(call(name, args))


def test_notifications_take_empty_arguments_and_refusal_has_no_tool_call():
    registry = AgentToolRegistry(default_tool_definitions())
    assert registry.decode(call("get_notification_summary", {})).decision == "get_notification_summary"
    assert registry.decode(json.dumps(dict(decision="refuse", reason="unsupported", tool_name=None,
                                            arguments=None))).decision == "refuse"
    with pytest.raises(ValueError):
        registry.decode(json.dumps(dict(decision="refuse", reason="unsupported", tool_name="lookup_ticket",
                                       arguments={})))


def test_follow_up_requires_both_ticket_lookup_and_knowledge_capability():
    tools = default_tool_definitions()
    raw = call("lookup_ticket", {"ticket_id": str(UUID(int=1))}, follow_up_knowledge=True)
    assert AgentToolRegistry(tools).decode(raw).follow_up_knowledge
    with pytest.raises(ValueError):
        AgentToolRegistry((tools[0],)).decode(raw)
    with pytest.raises(ValueError):
        AgentToolRegistry(tools).decode(call("get_notification_summary", {}, follow_up_knowledge=True))


def test_duplicate_registration_is_rejected():
    tool = default_tool_definitions()[0]
    with pytest.raises(ValueError):
        AgentToolRegistry((tool, tool))


def test_tool_invocation_validates_before_side_effect_and_injects_trusted_authentication():
    client = Mock()
    ticket = TicketLookupTool(client)
    with pytest.raises(ValidationError):
        ticket.invoke({"ticket_id": str(UUID(int=1)), "authorization": "forged"}, authorization="Bearer trusted")
    client.get_ticket.assert_not_called()
    ticket.invoke({"ticket_id": str(UUID(int=1))}, authorization="Bearer trusted")
    client.get_ticket.assert_called_once_with(UUID(int=1), authorization="Bearer trusted")
    notification = NotificationSummaryTool(client)
    with pytest.raises(ValidationError):
        notification.invoke({"owner_id": "someone else"}, authorization="Bearer trusted")
    client.get_notification_summary.assert_not_called()
    task = HumanHandoffTaskTool(client)
    task.invoke({"handoff_reason": "account_security_risk"}, request_id=UUID(int=2), authorization="Bearer trusted")
    client.create_handoff_task.assert_called_once_with(request_id=UUID(int=2),
        handoff_reason="account_security_risk", authorization="Bearer trusted")


def test_model_planner_graph_and_real_tool_adapter_share_the_same_question_contract():
    class Model:
        identity = "stub"
        def complete(self, **kwargs):
            return call("answer_support_knowledge", {"question": "campus wifi help"})
    provider = Mock()
    provider.answer.return_value = SupportKnowledgeAnswer(status="insufficient_evidence",
                                                         answer_text="no evidence", citations=())
    graph = CampusSupportTriageGraph(ModelTriagePlanner(Model()), TicketSpecialistAgent(TicketLookupTool(Mock())),
                                     KnowledgeSpecialistAgent(SupportKnowledgeAnswerTool(provider)))
    result = graph.invoke(user_query="campus wifi help")
    assert result["decision"] == "answer_support_knowledge"
    provider.answer.assert_called_once_with("campus wifi help", top_k=3)


def test_registry_errors_keep_the_existing_fallback_error_boundary():
    class Model:
        identity = "stub"
        def complete(self, **kwargs):
            return call("delete_ticket", {})
    with pytest.raises(TriagePlannerOutputError):
        ModelTriagePlanner(Model()).plan(user_query="unsupported")
