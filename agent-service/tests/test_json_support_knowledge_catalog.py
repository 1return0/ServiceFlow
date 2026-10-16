from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.infrastructure.persistence.json_support_knowledge_catalog import (
    JsonSupportKnowledgeCatalog,
    SupportKnowledgeCatalogLoadError,
)


class JsonSupportKnowledgeCatalogTest(TestCase):
    def test_loads_the_versioned_demonstration_campus_support_corpus(self) -> None:
        catalog = JsonSupportKnowledgeCatalog(
            Path("data/support-knowledge/demo-campus-support-v1.json")
        )

        articles = catalog.list_articles()

        self.assertEqual(5, len(articles))
        self.assertEqual("campus_network", articles[0].category)
        self.assertEqual("demo-campus-support-v1", articles[0].corpus_version)
        self.assertTrue(articles[0].source_reference.startswith("demo://"))
        self.assertEqual("demonstration", articles[0].source_kind)
        self.assertEqual("demonstration", articles[0].source_review_status)
        self.assertEqual(64, len(articles[0].source_content_sha256))

    def test_rejects_an_article_whose_content_does_not_match_its_fingerprint(self) -> None:
        catalog_text = """[
          {
            \"article_id\": \"network-v1\",
            \"category\": \"campus_network\",
            \"title\": \"Campus network\",
            \"content\": \"Tampered content\",
            \"source_reference\": \"https://it.example.edu/network\",
            \"source_kind\": \"official_campus\",
            \"source_content_sha256\": \"not-the-real-hash\",
            \"source_review_status\": \"reviewed\",
            \"source_review_reference\": \"manual://review/network-v1\",
            \"corpus_version\": \"campus-support-v1\"
          }
        ]"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(catalog_text, encoding="utf-8")

            with self.assertRaises(SupportKnowledgeCatalogLoadError):
                JsonSupportKnowledgeCatalog(path).list_articles()

    def test_rejects_an_official_campus_article_without_an_https_source(self) -> None:
        catalog_text = """[
          {
            \"article_id\": \"network-v1\",
            \"category\": \"campus_network\",
            \"title\": \"Campus network\",
            \"content\": \"Reset the network connection.\",
            \"source_reference\": \"http://it.example.edu/network\",
            \"source_kind\": \"official_campus\",
            \"source_content_sha256\": \"9d407f145ab4d5908d2ced0ea7b15e4fa73edb21489a564a936fcc3ffc9cb7dc\",
            \"source_review_status\": \"reviewed\",
            \"source_review_reference\": \"manual://review/network-v1\",
            \"corpus_version\": \"campus-support-v1\"
          }
        ]"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(catalog_text, encoding="utf-8")

            with self.assertRaises(SupportKnowledgeCatalogLoadError):
                JsonSupportKnowledgeCatalog(path).list_articles()

    def test_rejects_an_unreviewed_official_campus_source(self) -> None:
        catalog_text = """[
          {
            \"article_id\": \"network-v1\",
            \"category\": \"campus_network\",
            \"title\": \"Campus network\",
            \"content\": \"Reset the network connection.\",
            \"source_reference\": \"https://it.example.edu/network\",
            \"source_kind\": \"official_campus\",
            \"source_content_sha256\": \"9d407f145ab4d5908d2ced0ea7b15e4fa73edb21489a564a936fcc3ffc9cb7dc\",
            \"source_review_status\": \"demonstration\",
            \"source_review_reference\": \"manual://review/network-v1\",
            \"corpus_version\": \"campus-support-v1\"
          }
        ]"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(catalog_text, encoding="utf-8")

            with self.assertRaises(SupportKnowledgeCatalogLoadError):
                JsonSupportKnowledgeCatalog(path).list_articles()
