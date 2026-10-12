import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.application.support_knowledge_chunk_retrieval import SupportKnowledgeChunkSearchHit
from scripts.run_public_campus_retrieval_benchmark import (
    ROOT, CachedSearcher, build_fixture_corpus, clustered_intervals, read_fixture,
)


class PublicCampusBenchmarkTest(TestCase):
    def test_frozen_cases_have_verified_sources_and_exclude_queries_from_index(self):
        fixture, file_hash = read_fixture(ROOT / "benchmark.json")
        manifest = json.loads((ROOT / "sources-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(file_hash, manifest["dataset_sha256"])
        corpus, dataset, metadata = build_fixture_corpus(fixture)
        self.assertEqual(51, len(corpus.chunk_snapshot()[1]))
        self.assertEqual(153, len(dataset["cases"]))
        self.assertEqual(26, len(fixture["sources"]))
        chunks = {chunk.chunk_id: chunk for chunk in corpus.chunk_snapshot()[1]}
        for case in dataset["cases"]:
            self.assertNotIn(case["query"], "\n".join(chunk.text for chunk in chunks.values()))
            for judgment in case["judgments"]:
                self.assertIn(judgment["chunk_id"], chunks)
        self.assertFalse(fixture["human_reviewed"])
        self.assertEqual(153, len(metadata))
        for source in manifest["sources"]:
            self.assertEqual("passed", source["support_anchor_check"])
        self.assertTrue(all(article.source_review_status == "demonstration"
                            for article in corpus.list_articles()))

    def test_ranking_cache_reuses_real_results_and_does_not_cache_failure(self):
        fixture, _ = read_fixture(ROOT / "benchmark.json")
        corpus, _, _ = build_fixture_corpus(fixture)
        chunk = corpus.chunk_snapshot()[1][0]

        class Searcher:
            calls = 0
            def search(self, query, *, top_k):
                self.calls += 1
                if query == "failed":
                    raise RuntimeError("reranker-model-timeout")
                return (SupportKnowledgeChunkSearchHit(chunk, 0.5),)

        with TemporaryDirectory() as directory:
            delegate = Searcher()
            cached = CachedSearcher("test", delegate, {chunk.chunk_id: chunk}, Path(directory))
            self.assertEqual(cached.search("ok"), cached.search("ok"))
            self.assertEqual(1, delegate.calls)
            with self.assertRaisesRegex(RuntimeError, "reranker-model-timeout"):
                cached.search("failed")
            self.assertEqual(1, len(list(Path(directory).rglob("*.json"))))

    def test_clustered_intervals_preserve_zero_difference(self):
        metadata = {"one": {"source_id": "page-a"}, "two": {"source_id": "page-a"},
                    "three": {"source_id": "page-b"}}
        cases = [{"case_id": key, "recall_at_k": 1.0, "reciprocal_rank": 0.5, "ndcg_at_k": 0.5}
                 for key in metadata]
        variants = [{"variant": name, "cases": cases}
                    for name in ("bm25", "dense", "hybrid", "hybrid_rerank")]
        report = clustered_intervals(variants, metadata)
        self.assertEqual(2, report["clusters"])
        for comparison in report["comparisons"].values():
            self.assertTrue(all(value == {"difference": 0.0, "lower": 0.0, "upper": 0.0}
                                for value in comparison.values()))
