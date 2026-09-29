import os
import unittest
from unittest.mock import patch

from app.config import load_settings


class SettingsTest(unittest.TestCase):
    def test_loads_planner_model_settings_without_exposing_the_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SERVICEFLOW_PLANNER_MODEL_ENABLED": "true",
                "SERVICEFLOW_TRIAGE_MODEL_ENABLED": "true",
                "SERVICEFLOW_PLANNER_MODEL_BASE_URL": "https://example.test/v1",
                "SERVICEFLOW_PLANNER_MODEL_NAME": "qwen-plus",
                "SERVICEFLOW_PLANNER_MODEL_API_KEY_ENV": "TEST_DASHSCOPE_KEY",
                "TEST_DASHSCOPE_KEY": "test-key",
                "SERVICEFLOW_PLANNER_MODEL_TIMEOUT_SECONDS": "25",
                "SERVICEFLOW_BUSINESS_READ_MAX_ATTEMPTS": "3",
                "SERVICEFLOW_BUSINESS_READ_INITIAL_BACKOFF_SECONDS": "0.25",
                "SERVICEFLOW_OCR_ENABLED": "true",
                "SERVICEFLOW_OCR_MODEL_BASE_URL": "https://example.test/v1",
                "SERVICEFLOW_OCR_MODEL_NAME": "qwen-ocr-test",
                "SERVICEFLOW_OCR_MODEL_API_KEY_ENV": "TEST_OCR_KEY",
                "TEST_OCR_KEY": "ocr-test-key",
                "SERVICEFLOW_OCR_MODEL_TIMEOUT_SECONDS": "45",
                "SERVICEFLOW_OCR_RENDER_DPI": "200",
                "SERVICEFLOW_OCR_MAX_PAGE_PIXELS": "7000000",
            },
        ):
            settings = load_settings()

        self.assertTrue(settings.planner_model_enabled)
        self.assertTrue(settings.triage_model_enabled)
        self.assertEqual("https://example.test/v1", settings.planner_model_base_url)
        self.assertEqual("qwen-plus", settings.planner_model_name)
        self.assertEqual(
            "TEST_DASHSCOPE_KEY",
            settings.planner_model_api_key_environment_variable,
        )
        self.assertEqual(25.0, settings.planner_model_timeout_seconds)
        self.assertEqual("test-key", settings.planner_model_api_key)
        self.assertEqual(3, settings.business_service_read_max_attempts)
        self.assertEqual(
            0.25,
            settings.business_service_read_initial_backoff_seconds,
        )
        self.assertTrue(settings.ocr_enabled)
        self.assertEqual("https://example.test/v1", settings.ocr_model_base_url)
        self.assertEqual("qwen-ocr-test", settings.ocr_model_name)
        self.assertEqual("TEST_OCR_KEY", settings.ocr_model_api_key_environment_variable)
        self.assertEqual("ocr-test-key", settings.ocr_model_api_key)
        self.assertEqual(45.0, settings.ocr_model_timeout_seconds)
        self.assertEqual(200, settings.ocr_render_dpi)
        self.assertEqual(7_000_000, settings.ocr_max_page_pixels)

    def test_rejects_an_invalid_boolean_value(self) -> None:
        with patch.dict(
            os.environ,
            {"SERVICEFLOW_PLANNER_MODEL_ENABLED": "sometimes"},
        ):
            with self.assertRaises(ValueError):
                load_settings()


if __name__ == "__main__":
    unittest.main()
