from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.domain.ocr_evaluation import (
    OcrEvaluationCase,
    OcrEvaluationDataset,
    OcrKeyField,
)


class OcrEvaluationDatasetError(ValueError):
    """The immutable OCR evaluation input cannot be trusted."""


def load_ocr_evaluation_dataset(
    dataset_path: Path,
    *,
    project_root: Path,
) -> tuple[OcrEvaluationDataset, str]:
    raw_bytes = dataset_path.read_bytes()
    dataset_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw = json.loads(raw_bytes)
        cases = tuple(_load_case(item, project_root) for item in raw["cases"])
        dataset = OcrEvaluationDataset(
            dataset_id=_required_string(raw, "dataset_id"),
            dataset_version=_required_positive_int(raw, "dataset_version"),
            review_status=_review_status(raw),
            cases=cases,
        )
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise OcrEvaluationDatasetError("OCR evaluation dataset is invalid") from error
    if not cases:
        raise OcrEvaluationDatasetError("OCR evaluation dataset must contain cases")
    return dataset, dataset_sha256


def _load_case(raw: object, project_root: Path) -> OcrEvaluationCase:
    if not isinstance(raw, dict):
        raise OcrEvaluationDatasetError("OCR evaluation case must be an object")
    artifact_reference = _required_string(raw, "artifact_reference")
    expected_text_reference = _required_string(raw, "expected_text_reference")
    artifact_sha256 = _required_sha256(raw, "artifact_sha256")
    expected_text_sha256 = _required_sha256(raw, "expected_text_sha256")
    _verify_reference(project_root, artifact_reference, artifact_sha256)
    _verify_reference(project_root, expected_text_reference, expected_text_sha256)
    fields = tuple(_load_field(field) for field in raw.get("fields", []))
    return OcrEvaluationCase(
        case_id=_required_string(raw, "case_id"),
        artifact_reference=artifact_reference,
        artifact_sha256=artifact_sha256,
        expected_text_reference=expected_text_reference,
        expected_text_sha256=expected_text_sha256,
        tags=tuple(_required_non_blank_string(tag) for tag in raw.get("tags", [])),
        fields=fields,
    )


def _load_field(raw: object) -> OcrKeyField:
    if not isinstance(raw, dict):
        raise OcrEvaluationDatasetError("OCR field must be an object")
    selector = raw.get("selector")
    if not isinstance(selector, dict):
        raise OcrEvaluationDatasetError("OCR field selector must be an object")
    kind = _required_string(selector, "kind")
    if kind not in {"line", "after_prefix"}:
        raise OcrEvaluationDatasetError("OCR field selector kind is unsupported")
    return OcrKeyField(
        field_name=_required_string(raw, "field_name"),
        expected_value=_required_string(raw, "expected_value"),
        selector_kind=kind,
        selector_value=_required_string(selector, "value"),
        critical=bool(raw.get("critical", False)),
    )


def _verify_reference(project_root: Path, reference: str, expected_sha256: str) -> None:
    root = project_root.resolve()
    path = (root / reference).resolve()
    if root not in path.parents:
        raise OcrEvaluationDatasetError("OCR evaluation reference escaped project root")
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise OcrEvaluationDatasetError("OCR evaluation source content hash mismatch")


def _required_string(raw: dict[str, object], key: str) -> str:
    return _required_non_blank_string(raw[key])


def _required_non_blank_string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OcrEvaluationDatasetError("OCR evaluation value must be a non-blank string")
    return value.strip()


def _required_sha256(raw: dict[str, object], key: str) -> str:
    value = _required_string(raw, key)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise OcrEvaluationDatasetError("OCR evaluation SHA-256 must be lowercase hex")
    return value


def _required_positive_int(raw: dict[str, object], key: str) -> int:
    value = raw[key]
    if not isinstance(value, int) or value < 1:
        raise OcrEvaluationDatasetError("OCR evaluation version must be positive")
    return value


def _review_status(raw: dict[str, object]) -> str:
    value = _required_string(raw, "review_status")
    if value not in {"provisional", "reviewed"}:
        raise OcrEvaluationDatasetError("OCR evaluation review status is invalid")
    return value

