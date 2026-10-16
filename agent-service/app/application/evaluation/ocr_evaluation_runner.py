from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from app.application.evaluation.ocr_evaluation import OcrCaseEvaluation, evaluate_ocr_case
from app.application.evaluation.ocr_evaluation_dataset import load_ocr_evaluation_dataset
from app.application.evaluation.ocr_smoke import SupportKnowledgePdfParser
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


@dataclass(frozen=True)
class OcrEvaluationReport:
    dataset_id: str
    dataset_version: int
    dataset_sha256: str
    review_status: str
    recognizer_identity: str
    elapsed_seconds: float
    cases: tuple[OcrCaseEvaluation, ...]

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def run_ocr_evaluation(
    *,
    parser: SupportKnowledgePdfParser,
    recognizer_identity: str,
    dataset_path: Path,
    project_root: Path,
) -> OcrEvaluationReport:
    dataset, dataset_sha256 = load_ocr_evaluation_dataset(
        dataset_path,
        project_root=project_root,
    )
    started_at = perf_counter()
    results: list[OcrCaseEvaluation] = []
    for case in dataset.cases:
        artifact_path = project_root / case.artifact_reference
        artifact_bytes = artifact_path.read_bytes()
        artifact = SupportKnowledgeArtifact(
            artifact_id=f"artifact_{case.artifact_sha256}",
            source_reference=f"evaluation://{dataset.dataset_id}/{case.case_id}",
            source_kind="demonstration",
            document_format="pdf",
            storage_relative_path=str(artifact_path.relative_to(project_root)),
            byte_size=len(artifact_bytes),
            content_sha256=case.artifact_sha256,
        )
        parsed = parser.parse(artifact)
        expected_text = (project_root / case.expected_text_reference).read_text(
            encoding="utf-8"
        )
        results.append(
            evaluate_ocr_case(
                case,
                expected_text=expected_text,
                actual_text=parsed.text,
            )
        )
    return OcrEvaluationReport(
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset_sha256,
        review_status=dataset.review_status,
        recognizer_identity=recognizer_identity,
        elapsed_seconds=perf_counter() - started_at,
        cases=tuple(results),
    )

