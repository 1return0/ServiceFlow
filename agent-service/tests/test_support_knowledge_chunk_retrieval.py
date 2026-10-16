from __future__ import annotations

from unittest import TestCase

from app.application.retrieval.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever,
)
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk


class SupportKnowledgeChunkRetrievalTest(TestCase):
    def test_returns_the_matching_table_row_instead_of_the_whole_article(self) -> None:
        retriever = LexicalSupportKnowledgeChunkRetriever((
            SupportKnowledgeChunk("chunk-1", "network-guide-v1", "Connect to CampusNet.", 1, "paragraph:1:item:1", 0, 21, "v1"),
            SupportKnowledgeChunk("chunk-2", "network-guide-v1", "服务台 | A楼", 2, "table:2:item:1", 0, 8, "v1"),
        ))

        hits = retriever.search("服务台在哪", top_k=1)

        self.assertEqual(hits[0].chunk.chunk_id, "chunk-2")
        self.assertEqual(hits[0].chunk.fragment_location, "table:2:item:1")
