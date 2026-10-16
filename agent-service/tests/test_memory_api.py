from __future__ import annotations

from datetime import datetime, timezone
from unittest import TestCase

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import create_router
from app.application.memory.long_term_memory import LongTermMemoryEntry
from app.application.agent.trusted_subject import TrustedSubjectAuthenticationError
from app.config import Settings


class _MemoryRuntime:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], LongTermMemoryEntry] = {}
        self._turns: dict[str, tuple[dict[str, str], ...]] = {
            "serviceflow-java:student-a": (
                {"role": "user", "content": "How do I join campus Wi-Fi?"},
            ),
            "serviceflow-java:student-b": (
                {"role": "user", "content": "Where is the IT help desk?"},
            ),
        }

    @staticmethod
    def _owner_for(authorization: str | None) -> str:
        owners = {
            "Bearer verified-token-a": "serviceflow-java:student-a",
            "Bearer verified-token-b": "serviceflow-java:student-b",
        }
        if authorization not in owners:
            raise TrustedSubjectAuthenticationError("invalid")
        return owners[authorization]

    def list_authenticated_preferences(self, *, authorization: str | None):
        owner = self._owner_for(authorization)
        return tuple(
            entry
            for (entry_owner, _), entry in self._entries.items()
            if entry_owner == owner
        )

    def remember_preference(self, *, authorization: str | None, preference_key: str, preference_value: str, user_consented: bool):
        owner = self._owner_for(authorization)
        if not user_consented:
            raise ValueError("consent required")
        now = datetime.now(timezone.utc)
        previous = self._entries.get((owner, preference_key))
        entry = LongTermMemoryEntry(
            owner_id=owner,
            preference_key=preference_key,
            preference_value=preference_value,
            consented_at=now,
            created_at=previous.created_at if previous else now,
            updated_at=now,
            revision=previous.revision + 1 if previous else 1,
        )
        self._entries[(owner, preference_key)] = entry
        return entry

    def forget_preference(self, *, authorization: str | None, preference_key: str):
        owner = self._owner_for(authorization)
        return self._entries.pop((owner, preference_key), None) is not None

    def forget_all_preferences(self, *, authorization: str | None):
        owner = self._owner_for(authorization)
        keys = [key for key in self._entries if key[0] == owner]
        for key in keys:
            del self._entries[key]
        return len(keys)

    def get_authenticated_conversation_turns(self, *, authorization: str | None):
        return self._turns.get(self._owner_for(authorization), ())

    def clear_authenticated_conversation(self, *, authorization: str | None):
        owner = self._owner_for(authorization)
        return self._turns.pop(owner, None) is not None


class _UnavailableMemoryRuntime(_MemoryRuntime):
    def remember_preference(self, **_kwargs):
        raise RuntimeError("store is unavailable")


class MemoryApiTest(TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.state.campus_support_triage_runtime = _MemoryRuntime()
        app.include_router(create_router(Settings()))
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer verified-token-a"}

    def test_authenticated_owner_can_save_list_and_delete_preference(self) -> None:
        saved = self.client.put(
            "/api/v1/memory/preferences",
            headers=self.headers,
            json={
                "preference_key": "preferred_response_language",
                "preference_value": "en-US",
                "user_consented": True,
            },
        )
        listed = self.client.get(
            "/api/v1/memory/preferences", headers=self.headers
        )
        deleted = self.client.delete(
            "/api/v1/memory/preferences/preferred_response_language",
            headers=self.headers,
        )

        self.assertEqual(200, saved.status_code)
        self.assertEqual("en-US", saved.json()["preference_value"])
        self.assertEqual(1, len(listed.json()["preferences"]))
        self.assertEqual(204, deleted.status_code)

    def test_memory_api_requires_java_verified_bearer_subject(self) -> None:
        response = self.client.get("/api/v1/memory/preferences")

        self.assertEqual(401, response.status_code)

    def test_memory_api_does_not_leak_between_java_subjects(self) -> None:
        self.client.put(
            "/api/v1/memory/preferences",
            headers=self.headers,
            json={
                "preference_key": "preferred_response_language",
                "preference_value": "en-US",
                "user_consented": True,
            },
        )

        other = self.client.get(
            "/api/v1/memory/preferences",
            headers={"Authorization": "Bearer verified-token-b"},
        )

        self.assertEqual(200, other.status_code)
        self.assertEqual([], other.json()["preferences"])

    def test_memory_store_failure_is_a_safe_503(self) -> None:
        app = FastAPI()
        app.state.campus_support_triage_runtime = _UnavailableMemoryRuntime()
        app.include_router(create_router(Settings()))

        response = TestClient(app).put(
            "/api/v1/memory/preferences",
            headers=self.headers,
            json={
                "preference_key": "preferred_response_language",
                "preference_value": "en-US",
                "user_consented": True,
            },
        )

        self.assertEqual(503, response.status_code)
        self.assertNotIn("store is unavailable", response.json()["detail"])

    def test_conversation_api_is_java_subject_scoped_and_can_clear(self) -> None:
        before = self.client.get(
            "/api/v1/memory/conversation", headers=self.headers
        )
        cleared = self.client.delete(
            "/api/v1/memory/conversation", headers=self.headers
        )
        after = self.client.get(
            "/api/v1/memory/conversation", headers=self.headers
        )
        other = self.client.get(
            "/api/v1/memory/conversation",
            headers={"Authorization": "Bearer verified-token-b"},
        )

        self.assertEqual("How do I join campus Wi-Fi?", before.json()["turns"][0]["content"])
        self.assertEqual(204, cleared.status_code)
        self.assertEqual([], after.json()["turns"])
        self.assertEqual("Where is the IT help desk?", other.json()["turns"][0]["content"])
