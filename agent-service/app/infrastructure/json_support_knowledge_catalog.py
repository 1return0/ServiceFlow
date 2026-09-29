from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from app.domain.support_knowledge import SupportKnowledgeArticle


class SupportKnowledgeCatalogLoadError(RuntimeError):
    """The local demonstration support corpus could not be loaded."""


class _ArticlePayload(BaseModel):
    article_id: str
    category: str
    title: str
    content: str
    source_reference: str
    source_kind: Literal["official_campus", "demonstration"]
    source_content_sha256: str
    source_review_status: Literal["reviewed", "demonstration"]
    source_review_reference: str
    corpus_version: str


class JsonSupportKnowledgeCatalog:
    def __init__(self, path: Path) -> None:
        self._path = path

    def list_articles(self) -> tuple[SupportKnowledgeArticle, ...]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            rows = tuple(_ArticlePayload.model_validate(row) for row in payload)
        except (OSError, TypeError, ValidationError, json.JSONDecodeError) as error:
            raise SupportKnowledgeCatalogLoadError(
                f"could not load support knowledge catalog: {self._path.name}"
            ) from error

        try:
            articles = tuple(self._to_article(row) for row in rows)
        except (TypeError, ValueError) as error:
            raise SupportKnowledgeCatalogLoadError(
                "support knowledge catalog contains an invalid article "
                f"or source fingerprint: {self._path.name}"
            ) from error
        return articles

    @staticmethod
    def _to_article(row: _ArticlePayload) -> SupportKnowledgeArticle:
        JsonSupportKnowledgeCatalog._validate_source_reference(row)
        actual_sha256 = hashlib.sha256(
            f"{row.title}\n{row.content}".encode("utf-8")
        ).hexdigest()
        if actual_sha256 != row.source_content_sha256:
            raise ValueError("support knowledge source content hash mismatch")
        return SupportKnowledgeArticle(
            article_id=row.article_id,
            category=row.category,  # type: ignore[arg-type]
            title=row.title,
            content=row.content,
            source_reference=row.source_reference,
            source_kind=row.source_kind,
            source_content_sha256=row.source_content_sha256,
            source_review_status=row.source_review_status,
            source_review_reference=row.source_review_reference,
            corpus_version=row.corpus_version,
        )

    @staticmethod
    def _validate_source_reference(row: _ArticlePayload) -> None:
        if row.source_kind == "demonstration":
            if not row.source_reference.startswith("demo://"):
                raise ValueError("demonstration source must use demo://")
            if row.source_review_status != "demonstration":
                raise ValueError("demonstration source must retain its review status")
            return

        parsed = urlparse(row.source_reference)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("official campus source must use an HTTPS URL")
        if row.source_review_status != "reviewed":
            raise ValueError("official campus source must be reviewed")
        if not row.source_review_reference.strip():
            raise ValueError("official campus source must retain review evidence")
