"""Versioned, source-backed reports. Browser edits never rewrite retrieved facts."""
from __future__ import annotations

import re
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReportNotFoundError(LookupError):
    pass


class ReportConflictError(RuntimeError):
    pass


class ReportUnavailableError(RuntimeError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def safe_text(value: str) -> str:
    value = value.strip()
    if not value or any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise ValueError("report text is blank or contains control characters")
    if re.search(r"Bearer\s+\S+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{16,}", value):
        raise ValueError("credentials must not be saved in reports")
    return value


class ReportCitation(StrictModel):
    source_reference: str = Field(min_length=1, max_length=2048)
    evidence_id: str = Field(min_length=1, max_length=200)
    quoted_text: str | None = Field(default=None, max_length=1500)

    @field_validator("evidence_id", "quoted_text")
    @classmethod
    def safe_evidence(cls, value):
        return safe_text(value) if value is not None else None

    @field_validator("source_reference")
    @classmethod
    def public_source(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme == "demo" and re.fullmatch(r"demo://[A-Za-z0-9._/-]+", value) and ".." not in value:
            return value  # Explicit internal demonstration reference, never a public URL.
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("reports require HTTP sources or explicit demo references")
        return safe_text(value)


class ReportSection(StrictModel):
    section_id: str = Field(default_factory=lambda: str(uuid4()))
    heading: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    citations: tuple[ReportCitation, ...] = Field(min_length=1, max_length=30)

    @field_validator("heading", "body")
    @classmethod
    def clean(cls, value):
        return safe_text(value)


class ReportContent(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    sections: tuple[ReportSection, ...] = Field(min_length=1, max_length=20)
    user_notes: str = Field(default="", max_length=2000)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        return safe_text(value)

    @field_validator("user_notes")
    @classmethod
    def clean_notes(cls, value):
        return safe_text(value) if value.strip() else ""

    @model_validator(mode="after")
    def bounded(self):
        ids = [section.section_id for section in self.sections]
        if len(set(ids)) != len(ids) or sum(len(section.body) for section in self.sections) > 24000:
            raise ValueError("report sections are duplicate or too large")
        if len(self.model_dump_json().encode("utf-8")) > 90000:
            raise ValueError("report exceeds bounded export input size")
        return self


class ReportEdit(StrictModel):
    base_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    section_order: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=20)
    user_notes: str | None = Field(default=None, max_length=2000)


def preview_edit(content: ReportContent, edit: ReportEdit) -> ReportContent:
    sections = content.sections
    if edit.section_order is not None:
        selected = {section.section_id: section for section in sections}
        if len(set(edit.section_order)) != len(edit.section_order) or not set(edit.section_order) <= selected.keys():
            raise ValueError("edit selects duplicate or unknown sections")
        sections = tuple(selected[key] for key in edit.section_order)
    return ReportContent(title=edit.title if edit.title is not None else content.title,
        sections=sections, user_notes=edit.user_notes if edit.user_notes is not None else content.user_notes)
