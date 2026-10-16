from __future__ import annotations

import hashlib

from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
)
from app.domain.support_knowledge import (
    SupportKnowledgeArticle,
    SupportKnowledgeArticleMetadata,
)
from app.domain.support_knowledge_artifact import SupportKnowledgeArtifact


class SupportKnowledgeArticleAssemblyError(ValueError):
    """A parsed document and its reviewed metadata cannot form an article."""


class SupportKnowledgeArticleAssembler:
    """Combines extracted text with the human facts needed by retrieval."""

    def assemble(
        self,
        artifact: SupportKnowledgeArtifact,
        parsed_document: ParsedSupportKnowledgeDocument,
        metadata: SupportKnowledgeArticleMetadata,
    ) -> SupportKnowledgeArticle:
        if parsed_document.artifact_id != artifact.artifact_id:
            raise SupportKnowledgeArticleAssemblyError(
                "parsed document does not belong to the supplied artifact"
            )
        if metadata.source_reference != artifact.source_reference:
            raise SupportKnowledgeArticleAssemblyError(
                "reviewed source reference does not match the artifact"
            )
        if metadata.source_kind != artifact.source_kind:
            raise SupportKnowledgeArticleAssemblyError(
                "reviewed source kind does not match the artifact"
            )

        title = (parsed_document.title or metadata.fallback_title).strip()
        content = parsed_document.text.strip()
        if not title or not content:
            raise SupportKnowledgeArticleAssemblyError(
                "a retrievable article needs a non-blank title and content"
            )

        source_content_sha256 = hashlib.sha256(
            f"{title}\n{content}".encode("utf-8")
        ).hexdigest()
        return SupportKnowledgeArticle(
            article_id=metadata.article_id,
            category=metadata.category,
            title=title,
            content=content,
            source_reference=metadata.source_reference,
            source_kind=metadata.source_kind,
            source_content_sha256=source_content_sha256,
            source_review_status=metadata.source_review_status,
            source_review_reference=metadata.source_review_reference,
            corpus_version=metadata.corpus_version,
        )
