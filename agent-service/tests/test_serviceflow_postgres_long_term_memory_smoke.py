from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest import TestCase, skipUnless
from uuid import uuid4

from app.application.memory.long_term_memory import LongTermMemoryWrite
from app.config import load_settings
from app.infrastructure.persistence.postgres_long_term_memory_store import (
    open_postgres_long_term_memory_store,
)


@skipUnless(
    os.getenv("SERVICEFLOW_RUN_POSTGRES_MEMORY_SMOKE") == "true",
    "set SERVICEFLOW_RUN_POSTGRES_MEMORY_SMOKE=true for PostgreSQL smoke",
)
class ServiceFlowPostgresLongTermMemorySmokeTest(TestCase):
    def test_preference_persists_updates_deletes_and_stays_owner_scoped(self) -> None:
        dsn = load_settings().memory_postgres_dsn
        assert dsn is not None
        first_owner = f"serviceflow-memory-smoke-{uuid4()}"
        second_owner = f"serviceflow-memory-smoke-{uuid4()}"
        first_time = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
        changed_time = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)

        with open_postgres_long_term_memory_store(
            dsn,
            application_namespace="serviceflow",
        ) as store:
            try:
                first = store.upsert_preference(
                    LongTermMemoryWrite(
                        owner_id=first_owner,
                        preference_key="preferred_response_language",
                        preference_value="zh-CN",
                        consented_at=first_time,
                    )
                )
                changed = store.upsert_preference(
                    LongTermMemoryWrite(
                        owner_id=first_owner,
                        preference_key="preferred_response_language",
                        preference_value="en-US",
                        consented_at=changed_time,
                    )
                )
                store.upsert_preference(
                    LongTermMemoryWrite(
                        owner_id=second_owner,
                        preference_key="preferred_response_language",
                        preference_value="zh-CN",
                        consented_at=first_time,
                    )
                )

                self.assertEqual(1, first.revision)
                self.assertEqual(2, changed.revision)
                self.assertEqual(("en-US",), tuple(
                    entry.preference_value
                    for entry in store.list_preferences(first_owner)
                ))
                self.assertEqual(("zh-CN",), tuple(
                    entry.preference_value
                    for entry in store.list_preferences(second_owner)
                ))
                self.assertTrue(store.delete_preference(
                    first_owner,
                    "preferred_response_language",
                ))
                self.assertEqual((), store.list_preferences(first_owner))
                self.assertEqual(("zh-CN",), tuple(
                    entry.preference_value
                    for entry in store.list_preferences(second_owner)
                ))
            finally:
                store.delete_all_preferences(first_owner)
                store.delete_all_preferences(second_owner)
