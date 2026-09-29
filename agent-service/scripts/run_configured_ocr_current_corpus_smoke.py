from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
)
from app.application.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssembler,
)
from app.application.support_knowledge_ingestion_service import (
    SupportKnowledgeIngestionService,
)
from app.bootstrap import build_support_knowledge_document_parsing_service
from app.config import load_settings
from app.domain.support_knowledge import SupportKnowledgeArticleMetadata
from app.infrastructure.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
)
from app.infrastructure.in_memory_support_knowledge_corpus import (
    InMemoryCurrentSupportKnowledgeCorpus,
)


ARTIFACT_ROOT = PROJECT_ROOT / "data" / "ocr-smoke" / "artifacts"
ARTIFACT_FILENAME = "a667ad4036008c13fd577711ba8cde7c1a90f0222c24a941f73aecbb6248fe7f.pdf"
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "ocr-current-corpus-smoke"


def main() -> Path:
    settings = load_settings()
    if not settings.ocr_enabled:
        raise RuntimeError("SERVICEFLOW_OCR_ENABLED must be true for OCR smoke")
    content = (ARTIFACT_ROOT / ARTIFACT_FILENAME).read_bytes()
    corpus = InMemoryCurrentSupportKnowledgeCorpus(())
    parser = build_support_knowledge_document_parsing_service(ARTIFACT_ROOT, settings)
    service = SupportKnowledgeIngestionService(
        FileSystemSupportKnowledgeArtifactStore(ARTIFACT_ROOT),
        parser,
        SupportKnowledgeArticleAssembler(),
        corpus,
        FragmentAwareSupportKnowledgeChunker(),
    )
    try:
        result = service.ingest(
            source_reference="synthetic://serviceflow/ocr-current-corpus-v1",
            source_kind="demonstration",
            original_filename="synthetic-scan.pdf",
            content=content,
            metadata=SupportKnowledgeArticleMetadata(
                article_id="ocr-current-corpus-smoke-v1",
                category="service_process",
                fallback_title="Campus support OCR smoke",
                source_reference="synthetic://serviceflow/ocr-current-corpus-v1",
                source_kind="demonstration",
                source_review_status="demonstration",
                source_review_reference="ocr-current-corpus-smoke-v1",
                corpus_version="ocr-current-corpus-smoke-v1",
            ),
        )
    finally:
        service.close()

    if not result.chunks or any(
        chunk.fragment_location != "page:1:ocr" for chunk in result.chunks
    ):
        raise RuntimeError("OCR current-corpus smoke did not retain OCR provenance")
    output_path = REPORT_DIRECTORY / (
        "ocr-current-corpus-smoke-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + ".json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as report_file:
        json.dump(
            {
                "artifact_id": result.artifact.artifact_id,
                "article_id": result.article.article_id,
                "chunk_count": len(result.chunks),
                "fragment_locations": [
                    chunk.fragment_location for chunk in result.chunks
                ],
                "corpus_changed": result.corpus_changed,
                "corpus_revision": result.corpus_revision,
            },
            report_file,
            ensure_ascii=False,
            indent=2,
        )
        report_file.write("\n")
    return output_path


if __name__ == "__main__":
    created_path = main()
    print(f"OCR Current Corpus smoke report created: {created_path}")

