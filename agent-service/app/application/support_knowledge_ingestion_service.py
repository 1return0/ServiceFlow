from __future__ import annotations

from dataclasses import dataclass

from app.application.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssembler,
)
from app.application.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
)
from app.application.support_knowledge_document_parsing_service import (
    SupportKnowledgeDocumentParsingService,
)
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
)
from app.domain.support_knowledge import (
    SupportKnowledgeArticle,
    SupportKnowledgeArticleMetadata,
    CurrentSupportKnowledgeCorpus,
    SupportKnowledgeSourceKind,
)
from app.domain.support_knowledge_artifact import (
    SupportKnowledgeArtifact,
    SupportKnowledgeArtifactStore,
)
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


@dataclass(frozen=True)
class SupportKnowledgeIngestionResult:
    artifact: SupportKnowledgeArtifact
    parsed_document: ParsedSupportKnowledgeDocument
    article: SupportKnowledgeArticle
    chunks: tuple[SupportKnowledgeChunk, ...]
    corpus_changed: bool
    corpus_revision: int


class SupportKnowledgeIngestionService:
    """Coordinates raw-file storage, parsing, and reviewed article assembly."""

    def __init__(
        self,
        artifact_store: SupportKnowledgeArtifactStore,
        document_parsing_service: SupportKnowledgeDocumentParsingService,
        article_assembler: SupportKnowledgeArticleAssembler,
        current_corpus: CurrentSupportKnowledgeCorpus,
        chunker: FragmentAwareSupportKnowledgeChunker,
    ) -> None:
        self._artifact_store = artifact_store
        self._document_parsing_service = document_parsing_service
        self._article_assembler = article_assembler
        self._current_corpus = current_corpus
        self._chunker = chunker

    def ingest(
        self,
        *,
        source_reference: str,
        source_kind: SupportKnowledgeSourceKind,
        original_filename: str,
        content: bytes,
        metadata: SupportKnowledgeArticleMetadata,
    ) -> SupportKnowledgeIngestionResult:
        artifact = self._artifact_store.save(
            source_reference=source_reference,
            source_kind=source_kind,
            original_filename=original_filename,
            content=content,
        )
        parsed_document = self._document_parsing_service.parse(artifact)
        article = self._article_assembler.assemble(
            artifact,
            parsed_document,
            metadata,
        )
        chunks = self._chunker.chunk(article, parsed_document)
        corpus_changed = self._current_corpus.upsert_with_chunks(article, chunks)
        return SupportKnowledgeIngestionResult(
            artifact=artifact,
            parsed_document=parsed_document,
            article=article,
            chunks=chunks,
            corpus_changed=corpus_changed,
            corpus_revision=self._current_corpus.revision,
        )

    def close(self) -> None:
        self._document_parsing_service.close()
