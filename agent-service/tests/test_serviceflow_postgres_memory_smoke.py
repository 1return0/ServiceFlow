from __future__ import annotations

import os
import unittest

from app.application.trusted_subject import build_serviceflow_thread_id
from app.application.workflows.campus_support_triage_graph import (
    CampusSupportTriageGraph,
)
from app.config import load_settings
from app.domain.triage_plan import TriagePlan
from app.infrastructure.postgres_checkpointer import open_postgres_checkpointer


class _RefusePlanner:
    identity = "serviceflow-memory-smoke-planner"

    def __init__(self) -> None:
        self.queries: list[str] = []

    def plan(self, *, user_query: str) -> TriagePlan:
        self.queries.append(user_query)
        return TriagePlan(
            decision="refuse",
            reason="smoke test does not call external tools",
        )


@unittest.skipUnless(
    os.getenv("SERVICEFLOW_RUN_POSTGRES_MEMORY_SMOKE") == "true",
    "set SERVICEFLOW_RUN_POSTGRES_MEMORY_SMOKE=true for PostgreSQL smoke",
)
class ServiceFlowPostgresMemorySmokeTest(unittest.TestCase):
    def test_same_java_subject_recovers_previous_query_context(self) -> None:
        dsn = load_settings().memory_postgres_dsn
        assert dsn is not None
        owner_id = "serviceflow-java:memory-smoke-student"
        thread_id = build_serviceflow_thread_id(owner_id)
        planner = _RefusePlanner()
        with open_postgres_checkpointer(dsn) as checkpointer:
            graph = CampusSupportTriageGraph(
                planner,
                ticket_specialist=object(),
                knowledge_specialist=object(),
                checkpointer=checkpointer,
            )
            try:
                first = graph.invoke(
                    user_query="校园网无法连接",
                    owner_id=owner_id,
                    thread_id=thread_id,
                )
                second = graph.invoke(
                    user_query="我已经重启过了",
                    owner_id=owner_id,
                    thread_id=thread_id,
                )
                self.assertEqual("refuse", first["decision"])
                self.assertIn("校园网无法连接", planner.queries[1])
                self.assertIn("我已经重启过了", planner.queries[1])
            finally:
                checkpointer.delete_thread(thread_id)
