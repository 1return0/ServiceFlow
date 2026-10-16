from __future__ import annotations

from dataclasses import asdict, dataclass

from app.domain.ocr_evaluation import OcrEvaluationCase, OcrKeyField


@dataclass(frozen=True)
class OcrFieldEvaluation:
    field_name: str
    expected_value: str
    actual_value: str | None
    exact_match: bool
    critical: bool


@dataclass(frozen=True)
class OcrCaseEvaluation:
    case_id: str
    character_error_rate: float
    word_error_rate: float
    field_evaluations: tuple[OcrFieldEvaluation, ...]

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def evaluate_ocr_case(
    case: OcrEvaluationCase,
    *,
    expected_text: str,
    actual_text: str,
) -> OcrCaseEvaluation:
    """Compare fresh OCR output with reviewed text; never mutate gold data."""
    return OcrCaseEvaluation(
        case_id=case.case_id,
        character_error_rate=character_error_rate(expected_text, actual_text),
        word_error_rate=word_error_rate(expected_text, actual_text),
        field_evaluations=tuple(
            evaluate_key_field(field, actual_text) for field in case.fields
        ),
    )


def character_error_rate(expected: str, actual: str) -> float:
    """CER = character edit distance / number of golden characters."""
    expected = _normalize_document_text(expected)
    actual = _normalize_document_text(actual)
    return _edit_distance(expected, actual) / max(len(expected), 1)


def word_error_rate(expected: str, actual: str) -> float:
    """WER uses whitespace-delimited words; Chinese needs a future tokenizer policy."""
    expected = _normalize_document_text(expected)
    actual = _normalize_document_text(actual)
    expected_words = expected.split()
    actual_words = actual.split()
    return _edit_distance(expected_words, actual_words) / max(len(expected_words), 1)


def evaluate_key_field(field: OcrKeyField, actual_text: str) -> OcrFieldEvaluation:
    actual_value = _select_value(field, actual_text)
    return OcrFieldEvaluation(
        field_name=field.field_name,
        expected_value=field.expected_value,
        actual_value=actual_value,
        exact_match=(
            actual_value is not None
            and _normalize_field_value(actual_value)
            == _normalize_field_value(field.expected_value)
        ),
        critical=field.critical,
    )


def _select_value(field: OcrKeyField, actual_text: str) -> str | None:
    lines = tuple(line.strip() for line in actual_text.splitlines() if line.strip())
    if field.selector_kind == "line":
        line_number = int(field.selector_value)
        return lines[line_number - 1] if 0 < line_number <= len(lines) else None
    if field.selector_kind == "after_prefix":
        for line in lines:
            if line.startswith(field.selector_value):
                return line.removeprefix(field.selector_value).strip() or None
        return None
    raise ValueError("unsupported OCR field selector")


def _normalize_field_value(value: str) -> str:
    return " ".join(value.split())


def _normalize_document_text(value: str) -> str:
    """Ignore file line-ending and terminal-newline conventions, not text content."""
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _edit_distance[T](expected: list[T] | str, actual: list[T] | str) -> int:
    """Classic dynamic-programming Levenshtein distance, kept dependency-free."""
    previous = list(range(len(actual) + 1))
    for expected_index, expected_item in enumerate(expected, start=1):
        current = [expected_index]
        for actual_index, actual_item in enumerate(actual, start=1):
            substitution_cost = 0 if expected_item == actual_item else 1
            current.append(
                min(
                    previous[actual_index] + 1,
                    current[actual_index - 1] + 1,
                    previous[actual_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]
