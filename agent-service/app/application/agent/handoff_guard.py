from __future__ import annotations

from typing import Protocol

from app.domain.triage_plan import HandoffReason


class HandoffGuard(Protocol):
    """Detects high-risk requests that must not enter normal tool routing."""

    @property
    def identity(self) -> str:
        ...

    def detect(self, *, user_query: str) -> HandoffReason | None:
        ...


class CampusRiskHandoffGuard:
    """Small deterministic safety boundary before any planner or specialist runs."""

    _ACCOUNT_SECURITY_SIGNALS = ("账号被盗", "账号泄露", "密码泄露")
    _PHYSICAL_SAFETY_SIGNALS = ("冒烟", "火灾", "着火", "触电", "漏电")

    @property
    def identity(self) -> str:
        return "campus-risk-handoff-guard-v1"

    def detect(self, *, user_query: str) -> HandoffReason | None:
        normalized_query = user_query.strip()
        if any(signal in normalized_query for signal in self._ACCOUNT_SECURITY_SIGNALS):
            return "account_security_risk"
        if any(signal in normalized_query for signal in self._PHYSICAL_SAFETY_SIGNALS):
            return "physical_safety_risk"
        return None
