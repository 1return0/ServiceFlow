import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.ocr_evaluation_dataset import (
    OcrEvaluationDatasetError,
    load_ocr_evaluation_dataset,
)


class OcrEvaluationDatasetTest(TestCase):
    def test_loads_dataset_and_records_its_sha256(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "scan.pdf"
            expected = root / "gold.txt"
            artifact.write_bytes(b"fake-pdf")
            expected.write_text("Expected text\n", encoding="utf-8")
            dataset_path = root / "dataset.json"
            dataset_path.write_text(
                json.dumps(_dataset_payload(artifact, expected)), encoding="utf-8"
            )

            dataset, dataset_sha256 = load_ocr_evaluation_dataset(
                dataset_path,
                project_root=root,
            )

            self.assertEqual("test-ocr-v1", dataset.dataset_id)
            self.assertEqual(1, dataset.dataset_version)
            self.assertEqual(
                hashlib.sha256(dataset_path.read_bytes()).hexdigest(), dataset_sha256
            )

    def test_rejects_changed_golden_text(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "scan.pdf"
            expected = root / "gold.txt"
            artifact.write_bytes(b"fake-pdf")
            expected.write_text("changed\n", encoding="utf-8")
            dataset_path = root / "dataset.json"
            payload = _dataset_payload(artifact, expected)
            payload["cases"][0]["expected_text_sha256"] = "a" * 64
            dataset_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(
                OcrEvaluationDatasetError, "source content hash mismatch"
            ):
                load_ocr_evaluation_dataset(dataset_path, project_root=root)


def _dataset_payload(artifact: Path, expected: Path) -> dict[str, object]:
    return {
        "dataset_id": "test-ocr-v1",
        "dataset_version": 1,
        "review_status": "provisional",
        "cases": [
            {
                "case_id": "case-a",
                "artifact_reference": artifact.name,
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "expected_text_reference": expected.name,
                "expected_text_sha256": hashlib.sha256(expected.read_bytes()).hexdigest(),
                "tags": ["synthetic"],
                "fields": [],
            }
        ],
    }

