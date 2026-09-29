from __future__ import annotations

from unittest import TestCase

from app.application.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
    SupportKnowledgeChunkingError,
)
from app.domain.parsed_support_knowledge_document import (
    ParsedSupportKnowledgeDocument,
    ParsedSupportKnowledgeFragment,
)
from app.domain.support_knowledge import SupportKnowledgeArticle


def _article(content: str) -> SupportKnowledgeArticle:
    return SupportKnowledgeArticle(
        article_id="network-guide-v1", category="campus_network", title="Network",
        content=content, source_reference="https://it.example.edu/guide.docx",
        source_kind="official_campus", source_content_sha256="sha",
        source_review_status="reviewed", source_review_reference="review",
        corpus_version="v1",
    )


class FragmentAwareSupportKnowledgeChunkerTest(TestCase):
    def test_preserves_the_fragment_location_in_each_chunk(self) -> None:
        parsed = ParsedSupportKnowledgeDocument(
            artifact_id="artifact-1", document_format="docx", title="Network",
            text="Connect to CampusNet.\nService desk | Building A",
            fragments=(
                ParsedSupportKnowledgeFragment(1, "paragraph:1:item:1", "Connect to CampusNet."),
                ParsedSupportKnowledgeFragment(2, "table:2:item:1", "Service desk | Building A"),
            ),
        )

        chunks = FragmentAwareSupportKnowledgeChunker().chunk(_article(parsed.text), parsed)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1].fragment_location, "table:2:item:1")
        self.assertTrue(chunks[0].chunk_id.startswith("chunk_"))
        self.assertEqual(chunks[1].fragment_char_start, 0)

    def test_splits_a_long_fragment_with_a_deterministic_overlap(self) -> None:
        parsed = ParsedSupportKnowledgeDocument(
            artifact_id="artifact-1", document_format="html", title=None,
            text="abcdefghij", fragments=(
                ParsedSupportKnowledgeFragment(1, "html:body", "abcdefghij"),
            ),
        )

        chunks = FragmentAwareSupportKnowledgeChunker(
            max_chars=5, overlap_chars=2
        ).chunk(_article(parsed.text), parsed)

        self.assertEqual([chunk.text for chunk in chunks], ["abcde", "defgh", "ghij"])
        self.assertEqual(
            [(chunk.fragment_char_start, chunk.fragment_char_end) for chunk in chunks],
            [(0, 5), (3, 8), (6, 10)],
        )

    def test_prefers_a_sentence_boundary_before_falling_back_to_hard_length(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        parsed = ParsedSupportKnowledgeDocument(
            artifact_id="artifact-1", document_format="html", title=None,
            text=text,
            fragments=(ParsedSupportKnowledgeFragment(1, "html:body", text),),
        )

        chunks = FragmentAwareSupportKnowledgeChunker(
            max_chars=20, overlap_chars=0
        ).chunk(_article(text), parsed)

        self.assertEqual(
            [chunk.text for chunk in chunks],
            ["First sentence.", " Second sentence.", " Third sentence."],
        )

    def test_rejects_an_article_not_created_from_this_document(self) -> None:
        parsed = ParsedSupportKnowledgeDocument(
            artifact_id="artifact-1", document_format="html", title=None,
            text="Current text", fragments=(),
        )
        with self.assertRaises(SupportKnowledgeChunkingError):
            FragmentAwareSupportKnowledgeChunker().chunk(_article("Other text"), parsed)
