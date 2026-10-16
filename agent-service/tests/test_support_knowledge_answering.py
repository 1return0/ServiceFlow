from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from app.application.retrieval.support_knowledge_answering import (
    ExtractiveSupportKnowledgeAnswerService,
)
from app.application.retrieval.support_knowledge_retrieval import (
    LexicalSupportKnowledgeRetriever,
)
from app.infrastructure.persistence.json_support_knowledge_catalog import (
    JsonSupportKnowledgeCatalog,
)


class SupportKnowledgeAnswerServiceTest(TestCase):
    def setUp(self) -> None:
        retriever = LexicalSupportKnowledgeRetriever(
            JsonSupportKnowledgeCatalog(
                Path("data/support-knowledge/demo-campus-support-v1.json")
            )
        )
        self.service = ExtractiveSupportKnowledgeAnswerService(retriever)

    def test_answers_with_retrieved_content_and_source_citations(self) -> None:
        answer = self.service.answer("教学系统打不开，课程无法访问怎么办？")

        self.assertEqual("answered", answer.status)
        self.assertIn("教学系统", answer.answer_text)
        self.assertEqual(1, len(answer.citations))
        self.assertEqual("course-system-v1", answer.citations[0].article_id)
        self.assertTrue(answer.citations[0].source_reference.startswith("demo://"))

    def test_refuses_when_no_knowledge_evidence_is_retrieved(self) -> None:
        answer = self.service.answer("食堂今天有什么菜？")

        self.assertEqual("insufficient_evidence", answer.status)
        self.assertEqual((), answer.citations)
