from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Protocol

from app.domain.parsed_support_knowledge_document import ParsedSupportKnowledgeDocument
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class SupportKnowledgePdfParser(Protocol):
    def parse(
        self,
        artifact: SupportKnowledgeArtifact,
    ) -> ParsedSupportKnowledgeDocument:
        ...


@dataclass(frozen=True)
class OcrSmokeReport:
    artifact_id: str
    artifact_sha256: str
    recognizer_identity: str
    elapsed_seconds: float
    page_count: int
    character_count: int
    fragment_locations: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def run_ocr_smoke(
    *,
    parser: SupportKnowledgePdfParser,
    artifact: SupportKnowledgeArtifact,
    recognizer_identity: str,
) -> OcrSmokeReport:
    """Runs one explicit OCR smoke; persistence and quality scoring stay separate."""
    started_at = perf_counter()
    parsed = parser.parse(artifact)
    elapsed_seconds = perf_counter() - started_at
    locations = tuple(fragment.location for fragment in parsed.fragments)
    if not locations or any(not location.endswith(":ocr") for location in locations):
        raise ValueError("OCR smoke artifact did not traverse the OCR fallback path")
    return OcrSmokeReport(
        artifact_id=artifact.artifact_id,
        artifact_sha256=artifact.content_sha256,
        recognizer_identity=recognizer_identity,
        elapsed_seconds=elapsed_seconds,
        page_count=len(parsed.fragments),
        character_count=len(parsed.text),
        fragment_locations=locations,
    )
