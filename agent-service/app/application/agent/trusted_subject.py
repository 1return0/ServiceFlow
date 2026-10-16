"""Resolve a memory owner only from Java's verified identity contract."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Protocol

from app.infrastructure.clients.business_client import BusinessAuthenticatedSubject


class TrustedSubjectAuthenticationError(PermissionError):
    """A supplied Authorization header is not a usable Bearer credential."""


class AuthenticatedSubjectReader(Protocol):
    def get_authenticated_subject(
        self,
        *,
        authorization: str,
    ) -> BusinessAuthenticatedSubject:
        ...


@dataclass(frozen=True, slots=True)
class TrustedSubject:
    owner_id: str
    roles: tuple[str, ...]


class JavaTrustedSubjectResolver:
    """Never decodes JWT text; Java is the identity authority."""

    def __init__(self, reader: AuthenticatedSubjectReader) -> None:
        self._reader = reader

    def resolve(self, authorization: str | None) -> TrustedSubject:
        if authorization is None or not authorization.startswith("Bearer "):
            raise TrustedSubjectAuthenticationError(
                "a Bearer token is required to resolve a trusted subject"
            )
        if not authorization.removeprefix("Bearer ").strip():
            raise TrustedSubjectAuthenticationError(
                "a Bearer token must not be blank"
            )
        authenticated = self._reader.get_authenticated_subject(
            authorization=authorization,
        )
        subject = authenticated.subject.strip()
        if not subject:
            raise ValueError("Java authenticated subject must not be blank")
        return TrustedSubject(
            owner_id=f"serviceflow-java:{subject}",
            roles=authenticated.roles,
        )


def build_serviceflow_thread_id(owner_id: str) -> str:
    """Derive a stable checkpoint key without exposing Java's subject."""
    normalized = owner_id.strip()
    if not normalized:
        raise ValueError("trusted owner_id must not be blank")
    return "serviceflow-owner-" + hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()
