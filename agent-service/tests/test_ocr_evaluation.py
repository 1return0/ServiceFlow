from unittest import TestCase

from app.application.evaluation.ocr_evaluation import (
    character_error_rate,
    evaluate_key_field,
    word_error_rate,
)
from app.domain.ocr_evaluation import OcrKeyField


class OcrEvaluationTest(TestCase):
    def test_character_error_rate_uses_edit_distance_over_golden_length(self) -> None:
        self.assertEqual(0.2, character_error_rate("abcde", "abxde"))

    def test_word_error_rate_uses_whitespace_delimited_words(self) -> None:
        self.assertEqual(0.5, word_error_rate("network reset", "network"))

    def test_metrics_ignore_a_terminal_newline_from_the_gold_file(self) -> None:
        self.assertEqual(0.0, character_error_rate("Campus support\n", "Campus support"))

    def test_key_field_compares_a_selected_ocr_value_to_human_gold(self) -> None:
        field = OcrKeyField(
            field_name="location",
            expected_value="Library 1F",
            selector_kind="after_prefix",
            selector_value="Location:",
            critical=True,
        )

        evaluation = evaluate_key_field(
            field,
            "Campus IT Support\nLocation: Library 1F",
        )

        self.assertEqual("Library 1F", evaluation.actual_value)
        self.assertTrue(evaluation.exact_match)
        self.assertTrue(evaluation.critical)

    def test_missing_selected_field_is_not_an_exact_match(self) -> None:
        field = OcrKeyField(
            field_name="location",
            expected_value="Library 1F",
            selector_kind="after_prefix",
            selector_value="Location:",
            critical=True,
        )

        evaluation = evaluate_key_field(field, "Campus IT Support")

        self.assertIsNone(evaluation.actual_value)
        self.assertFalse(evaluation.exact_match)
