from __future__ import annotations

from unittest import TestCase

from app.application.knowledge.knowledge_import_access_policy import (
    KnowledgeImportAccessPolicy,
    KnowledgeImportAuthorizationError,
    KnowledgeImportDisabledError,
)
from app.config import Settings


class KnowledgeImportAccessPolicyTest(TestCase):
    def test_is_disabled_by_default(self) -> None:
        policy = KnowledgeImportAccessPolicy.from_settings(Settings())

        with self.assertRaises(KnowledgeImportDisabledError):
            policy.require_authorized("any-token")

    def test_enabled_import_requires_a_dedicated_secret(self) -> None:
        with self.assertRaisesRegex(ValueError, "ADMIN_TOKEN is required"):
            KnowledgeImportAccessPolicy.from_settings(
                Settings(knowledge_import_enabled=True)
            )

    def test_rejects_a_wrong_secret_and_accepts_the_configured_secret(self) -> None:
        policy = KnowledgeImportAccessPolicy(
            enabled=True,
            admin_token="expected-secret",
        )

        with self.assertRaises(KnowledgeImportAuthorizationError):
            policy.require_authorized("wrong-secret")
        policy.require_authorized("expected-secret")
