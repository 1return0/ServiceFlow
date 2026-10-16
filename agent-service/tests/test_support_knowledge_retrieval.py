from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from app.application.retrieval.support_knowledge_retrieval import (
    LexicalSupportKnowledgeRetriever,
)
from app.infrastructure.persistence.json_support_knowledge_catalog import (
    JsonSupportKnowledgeCatalog,
)


class SupportKnowledgeRetrievalTest(TestCase):
    def setUp(self) -> None:
        self.retriever = LexicalSupportKnowledgeRetriever(
            JsonSupportKnowledgeCatalog(
                Path("data/support-knowledge/demo-campus-support-v1.json")
            )
        )

    def test_ranks_the_teaching_system_article_for_a_course_access_question(self) -> None:
        hits = self.retriever.search(
            "教学系统打不开，某门课程无法访问怎么办？"
        )

        self.assertEqual("course-system-v1", hits[0].article.article_id)
        self.assertTrue(hits[0].score > 0)
        self.assertTrue(hits[0].article.source_reference.startswith("demo://"))

    def test_rejects_a_blank_query(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be blank"):
            self.retriever.search("  ")

    def test_returns_only_positive_score_hits_up_to_top_k(self) -> None:
        hits = self.retriever.search("校园网认证失败", top_k=1)

        self.assertEqual(1, len(hits))
        self.assertEqual("network-self-service-v1", hits[0].article.article_id)
