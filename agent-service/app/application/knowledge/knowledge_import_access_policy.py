from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.config import Settings


class KnowledgeImportDisabledError(RuntimeError):
    """The deployment has intentionally not exposed knowledge ingestion."""


class KnowledgeImportAuthorizationError(RuntimeError):
    """The caller did not prove possession of the dedicated import credential."""


@dataclass(frozen=True, slots=True)
class KnowledgeImportAccessPolicy:
    """Default-closed boundary for the write-side knowledge ingestion API.

    The Agent process intentionally does not copy the Java JWT signing key. In a
    real deployment, an API gateway or an identity service would authenticate an
    administrator before this service. For this student deployment, a distinct
    deployment secret isolates the high-risk import operation from ordinary
    knowledge-answer requests.
    """

    enabled: bool
    admin_token: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> "KnowledgeImportAccessPolicy":
        if settings.knowledge_import_enabled and not settings.knowledge_import_admin_token:
            raise ValueError(
                "SERVICEFLOW_KNOWLEDGE_IMPORT_ADMIN_TOKEN is required when "
                "SERVICEFLOW_KNOWLEDGE_IMPORT_ENABLED=true"
            )
        return cls(
            enabled=settings.knowledge_import_enabled,
            admin_token=settings.knowledge_import_admin_token,
        )

    def require_authorized(self, provided_token: str | None) -> None:
        if not self.enabled:
            raise KnowledgeImportDisabledError("knowledge import is disabled")
        if (
            provided_token is None
            or self.admin_token is None
            or not secrets.compare_digest(provided_token, self.admin_token)
        ):
            raise KnowledgeImportAuthorizationError(
                "knowledge import credential is invalid"
            )
