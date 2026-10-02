from unittest import TestCase

from app.application.trusted_subject import (
    JavaTrustedSubjectResolver,
    TrustedSubjectAuthenticationError,
)
from app.infrastructure.business_client import BusinessAuthenticatedSubject


class _Reader:
    def __init__(self) -> None:
        self.authorization: str | None = None

    def get_authenticated_subject(self, *, authorization: str):
        self.authorization = authorization
        return BusinessAuthenticatedSubject(
            subject="student-001",
            roles=("STUDENT",),
        )


class JavaTrustedSubjectResolverTest(TestCase):
    def test_uses_java_response_as_owner_and_never_decodes_jwt_locally(self) -> None:
        reader = _Reader()
        resolved = JavaTrustedSubjectResolver(reader).resolve(
            "Bearer java-verified-token"
        )

        self.assertEqual("Bearer java-verified-token", reader.authorization)
        self.assertEqual("serviceflow-java:student-001", resolved.owner_id)
        self.assertEqual(("STUDENT",), resolved.roles)

    def test_rejects_absent_or_blank_bearer_before_java_call(self) -> None:
        resolver = JavaTrustedSubjectResolver(_Reader())
        for value in (None, "Basic anything", "Bearer   "):
            with self.subTest(value=value):
                with self.assertRaises(TrustedSubjectAuthenticationError):
                    resolver.resolve(value)
