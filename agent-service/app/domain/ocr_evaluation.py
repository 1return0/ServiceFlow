from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OcrFieldSelectorKind = Literal["line", "after_prefix"]


@dataclass(frozen=True)
class OcrKeyField:
    """One human-reviewed business value expected in an OCR case."""

    field_name: str
    expected_value: str
    selector_kind: OcrFieldSelectorKind
    selector_value: str
    critical: bool


@dataclass(frozen=True)
class OcrEvaluationCase:
    case_id: str
    artifact_reference: str
    artifact_sha256: str
    expected_text_reference: str
    expected_text_sha256: str
    tags: tuple[str, ...]
    fields: tuple[OcrKeyField, ...]


@dataclass(frozen=True)
class OcrEvaluationDataset:
    dataset_id: str
    dataset_version: int
    review_status: Literal["provisional", "reviewed"]
    cases: tuple[OcrEvaluationCase, ...]

