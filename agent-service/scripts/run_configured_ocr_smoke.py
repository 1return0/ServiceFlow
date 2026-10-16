from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.evaluation.ocr_smoke import run_ocr_smoke
from app.bootstrap import build_support_knowledge_document_parsing_service
from app.config import load_settings
from app.infrastructure.persistence.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
)


ARTIFACT_ROOT = PROJECT_ROOT / "data" / "ocr-smoke" / "artifacts"
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "ocr-smoke"


def main() -> Path:
    settings = load_settings()
    if not settings.ocr_enabled:
        raise RuntimeError("SERVICEFLOW_OCR_ENABLED must be true for a real OCR smoke")
    if not settings.ocr_model_base_url or not settings.ocr_model_api_key:
        raise RuntimeError("real OCR endpoint configuration is incomplete")

    artifact = FileSystemSupportKnowledgeArtifactStore(ARTIFACT_ROOT).save(
        source_reference="synthetic://serviceflow/ocr-smoke-v1",
        source_kind="demonstration",
        original_filename="synthetic-scan.pdf",
        content=_synthetic_scan_pdf_bytes(),
    )
    parser = build_support_knowledge_document_parsing_service(
        ARTIFACT_ROOT,
        settings,
    )
    try:
        report = run_ocr_smoke(
            parser=parser,
            artifact=artifact,
            recognizer_identity=(
                "openai-compatible-vision-ocr:"
                f"{settings.ocr_model_name}:campus-support-ocr-prompt-v1"
            ),
        )
    finally:
        parser.close()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = REPORT_DIRECTORY / f"ocr-smoke-{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as report_file:
        json.dump(report.as_json(), report_file, ensure_ascii=False, indent=2)
        report_file.write("\n")
    return output_path


def _synthetic_scan_pdf_bytes() -> bytes:
    image = Image.new("RGB", (1200, 700), "white")
    try:
        canvas = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=34)
        canvas.multiline_text(
            (80, 100),
            "Campus IT Support\nNetwork access reset\nLocation: Library 1F",
            fill="black",
            font=font,
            spacing=28,
        )
        with BytesIO() as output:
            image.save(output, format="PDF", resolution=144.0)
            return output.getvalue()
    finally:
        image.close()


if __name__ == "__main__":
    created_path = main()
    print(f"OCR smoke report created: {created_path}")
