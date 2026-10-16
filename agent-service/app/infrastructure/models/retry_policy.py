from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundedRetryPolicy:
    """Small retry policy for idempotent reads of a transient dependency."""

    max_attempts: int = 2
    initial_backoff_seconds: float = 0.1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds must not be negative")

    def delay_before_retry(self, completed_attempts: int) -> float:
        if completed_attempts < 1:
            raise ValueError("completed_attempts must be positive")
        return self.initial_backoff_seconds * (2 ** (completed_attempts - 1))
