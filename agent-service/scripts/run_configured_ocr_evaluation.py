from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.ocr_evaluation_runner import run_ocr_evaluation
from app.bootstrap import build_support_knowledge_document_parsing_service
from app.config import load_settings


DATASET_PATH = (
    PROJECT_ROOT / "data" / "ocr-evaluation" / "datasets" / "campus-support-ocr-v1.json"
)
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "ocr-evaluation"


def main() -> Path:
    settings = load_settings()
    if not settings.ocr_enabled:
        raise RuntimeError("SERVICEFLOW_OCR_ENABLED must be true for OCR evaluation")
    parser = build_support_knowledge_document_parsing_service(PROJECT_ROOT, settings)
    try:
        report = run_ocr_evaluation(
            parser=parser,
            recognizer_identity=(
                "openai-compatible-vision-ocr:"
                f"{settings.ocr_model_name}:campus-support-ocr-prompt-v1"
            ),
            dataset_path=DATASET_PATH,
            project_root=PROJECT_ROOT,
        )
    finally:
        parser.close()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = REPORT_DIRECTORY / f"ocr-evaluation-{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as report_file:
        json.dump(report.as_json(), report_file, ensure_ascii=False, indent=2)
        report_file.write("\n")
    return output_path


if __name__ == "__main__":
    created_path = main()
    print(f"OCR evaluation report created: {created_path}")

