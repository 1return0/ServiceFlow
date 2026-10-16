"""Isolated source-grounded benchmark using ServiceFlow's real retrieval adapters."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from collections import OrderedDict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

import httpx

from app.application.evaluation.retrieval_comparison_evaluation import run_retrieval_comparison_evaluation
from app.application.retrieval.support_knowledge_chunk_retrieval import (
    LexicalSupportKnowledgeChunkRetriever, SupportKnowledgeChunkSearchHit,
)
from app.domain.support_knowledge import SupportKnowledgeArticle
from app.domain.support_knowledge_chunk import SupportKnowledgeChunk
from app.infrastructure.parsers.html_support_knowledge_artifact_parser import _HtmlTextCollector
from app.infrastructure.persistence.in_memory_support_knowledge_corpus import InMemoryCurrentSupportKnowledgeCorpus

ROOT = Path("data/retrieval-evaluation/public-campus-v1")
QUERY_TYPES = ("direct", "colloquial", "constraint")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_fixture(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    fixture = json.loads(raw)
    if fixture["human_reviewed"] or fixture["annotation_status"] != "source_grounded_agent_authored":
        raise ValueError("benchmark annotation provenance is incorrect")
    ids = [row["id"] for row in fixture["records"]]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("benchmark records must have unique IDs")
    queries = []
    for row in fixture["records"]:
        if row["source_id"] not in fixture["sources"] or not row["anchors"] or not row["text"].strip():
            raise ValueError("record has missing source, anchors or evidence")
        if tuple(row["queries"]) != QUERY_TYPES:
            raise ValueError("each record needs the three declared query types")
        for kind, query in row["queries"].items():
            if not query.strip() or query in row["text"]:
                raise ValueError("queries must not be blank or embedded in evidence")
            if any(target not in ids for target in row.get("additional_judgments", {}).get(kind, [])):
                raise ValueError("judgment refers to an unknown record")
            queries.append(query)
    if len(queries) != len(set(queries)):
        raise ValueError("benchmark queries must be unique")
    for url in fixture["sources"].values():
        if urlparse(url).scheme != "https" or not (urlparse(url).hostname or "").endswith(".bnu.edu.cn"):
            raise ValueError("benchmark source must be an allowlisted official HTTPS site")
    return fixture, digest(raw)


def collect_sources(fixture: dict, fixture_hash: str, cache: Path, output: Path) -> None:
    """Keep raw downloaded pages locally; publish only hashes and support checks."""
    cache.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset_sha256": fixture_hash, "fetched_at": datetime.now(UTC).isoformat(), "sources": []}
    with httpx.Client(timeout=30, trust_env=False, follow_redirects=True) as client:
        for source_id, url in fixture["sources"].items():
            path = cache / f"{source_id}.html"
            if not path.exists():
                response = client.get(url)
                response.raise_for_status()
                if not (urlparse(str(response.url)).hostname or "").endswith(".bnu.edu.cn"):
                    raise ValueError("source redirected outside the official domain")
                path.write_bytes(response.content)
            raw = path.read_bytes()
            collector = _HtmlTextCollector()
            collector.feed(raw.decode("utf-8"))
            normalized = re.sub(r"\s+", "", collector.text)
            rows = [row for row in fixture["records"] if row["source_id"] == source_id]
            for row in rows:
                for anchor in row["anchors"]:
                    if re.sub(r"\s+", "", anchor) not in normalized:
                        raise ValueError(f"missing source support: {row['id']} / {anchor}")
            manifest["sources"].append({
                "source_id": source_id, "url": url, "artifact_sha256": digest(raw),
                "normalized_text_sha256": digest(normalized.encode()),
                "checked_record_ids": [row["id"] for row in rows],
                "support_anchor_check": "passed",
            })
            print(f"Verified source: {source_id} ({len(rows)} evidence units)", flush=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def build_fixture_corpus(fixture: dict):
    corpus = InMemoryCurrentSupportKnowledgeCorpus(())
    chunk_ids = {row["id"]: "chunk_" + digest((row["id"] + "\n" + row["text"]).encode())
                 for row in fixture["records"]}
    cases, case_metadata = [], {}
    for row in fixture["records"]:
        source = fixture["sources"][row["source_id"]]
        article = SupportKnowledgeArticle(
            article_id=row["id"], category="service_process", title=row["section"],
            content=row["text"], source_reference=source,
            source_kind="demonstration", source_review_status="demonstration",
            source_review_reference="agent-authored evaluation fixture; not human-reviewed",
            source_content_sha256=digest((row["section"] + "\n" + row["text"]).encode()),
            corpus_version=fixture["dataset_id"],
        )
        chunk = SupportKnowledgeChunk(
            chunk_id=chunk_ids[row["id"]], article_id=row["id"], text=row["text"],
            fragment_ordinal=1, fragment_location=f"web:{row['source_id']}:{row['section']}",
            fragment_char_start=0, fragment_char_end=len(row["text"]),
            chunker_version="public-campus-answer-unit-v1",
        )
        corpus.upsert_with_chunks(article, (chunk,))
        for kind, query in row["queries"].items():
            case_id = f"{row['id']}:{kind}"
            targets = [row["id"]] + row.get("additional_judgments", {}).get(kind, [])
            cases.append({"case_id": case_id, "query": query, "judgments": [
                {"chunk_id": chunk_ids[target], "relevance_grade": 1} for target in targets
            ]})
            case_metadata[case_id] = {"source_id": row["source_id"], "query_type": kind,
                                      "record_id": row["id"], "query": query}
    return corpus, {"dataset_id": fixture["dataset_id"], "dataset_version": 1, "cases": cases}, case_metadata


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


class QueryCachingEmbedder:
    def __init__(self, delegate, cache: Path):
        self.delegate, self.cache = delegate, cache

    @property
    def embedding_identity(self):
        return self.delegate.embedding_identity

    def embed_documents(self, texts):
        return self.delegate.embed_documents(texts)

    def embed_query(self, query):
        path = self.cache / (digest(query.encode()) + ".json")
        if path.exists():
            values = json.loads(path.read_text(encoding="utf-8"))
        else:
            values = self.delegate.embed_query(query)
            atomic_json(path, values)
        if len(values) != self.embedding_identity.dimension or not all(math.isfinite(v) for v in values):
            raise ValueError("cached query embedding is invalid")
        return tuple(values)

    def close(self):
        self.delegate.close()


class CachedSearcher:
    def __init__(self, name, delegate, chunks, cache: Path):
        self.name, self.delegate, self.chunks, self.cache = name, delegate, chunks, cache
        self.completed = 0

    def search(self, query, *, top_k=5):
        if top_k > 10:
            raise ValueError("frozen benchmark supports at most ten ranked results")
        path = self.cache / self.name / (digest(query.encode()) + ".json")
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
        else:
            hits = self.delegate.search(query, top_k=10)
            rows = [{"chunk_id": hit.chunk.chunk_id, "score": hit.score} for hit in hits]
            atomic_json(path, rows)
        ids = [row["chunk_id"] for row in rows]
        if len(ids) != len(set(ids)) or any(key not in self.chunks for key in ids):
            raise ValueError("cached ranking has invalid evidence IDs")
        if any(not math.isfinite(row["score"]) for row in rows):
            raise ValueError("cached ranking has an invalid score")
        self.completed += 1
        if self.completed % 15 == 0:
            print(f"{self.name}: {self.completed} searches", flush=True)
        return tuple(SupportKnowledgeChunkSearchHit(self.chunks[row["chunk_id"]], row["score"])
                     for row in rows[:top_k])


def aggregate(rows):
    return {key: sum(row[key] for row in rows) / len(rows)
            for key in ("recall_at_k", "reciprocal_rank", "ndcg_at_k")}


def clustered_intervals(variants: list[dict], metadata: dict) -> dict:
    """Resample source pages, keeping questions from the same page together."""
    by_name = {variant["variant"]: {row["case_id"]: row for row in variant["cases"]}
               for variant in variants}
    groups = {}
    for key, meta in metadata.items():
        groups.setdefault(meta["source_id"], []).append(key)
    source_ids = sorted(groups)
    result = {}
    for candidate, baseline in (("hybrid", "bm25"), ("hybrid_rerank", "bm25"),
                                ("hybrid_rerank", "hybrid"), ("hybrid_rerank", "dense")):
        metrics = {}
        for metric in ("recall_at_k", "reciprocal_rank", "ndcg_at_k"):
            differences = {key: by_name[candidate][key][metric] - by_name[baseline][key][metric]
                           for key in metadata}
            sums = {source: sum(differences[key] for key in groups[source]) for source in source_ids}
            rng = random.Random(20261012)
            samples = []
            for _ in range(10_000):
                picked = rng.choices(source_ids, k=len(source_ids))
                samples.append(sum(sums[source] for source in picked)
                               / sum(len(groups[source]) for source in picked))
            samples.sort()
            metrics[metric] = {"difference": sum(differences.values()) / len(differences),
                               "lower": samples[249], "upper": samples[9749]}
        result[f"{candidate}_minus_{baseline}"] = metrics
    return {"method": "paired source-page cluster bootstrap", "clusters": len(groups),
            "resamples": 10_000, "seed": 20261012, "comparisons": result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "benchmark.json")
    parser.add_argument("--collect-sources", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("reports/public-campus-retrieval-v1-real-20261012.json"))
    args = parser.parse_args()
    fixture, fixture_hash = read_fixture(args.dataset)
    cache = Path("data/retrieval-evaluation/.cache")
    manifest_path = args.dataset.parent / "sources-manifest.json"
    if args.collect_sources:
        collect_sources(fixture, fixture_hash, cache / "public-campus-sources", manifest_path)
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["dataset_sha256"] != fixture_hash:
        raise ValueError("source verification does not match frozen dataset")
    if {row["source_id"] for row in manifest["sources"]} != set(fixture["sources"]):
        raise ValueError("source manifest is incomplete")
    for source in manifest["sources"]:
        expected = {row["id"] for row in fixture["records"] if row["source_id"] == source["source_id"]}
        if source["support_anchor_check"] != "passed" or set(source["checked_record_ids"]) != expected:
            raise ValueError("source manifest lacks verified evidence units")
    if args.output.exists():
        raise FileExistsError("completed benchmark reports must not be overwritten")

    # Real configuration is loaded only for a requested model run, never source collection.
    from app.config import load_settings
    from app.bootstrap import build_support_knowledge_text_embedder
    from app.application.retrieval.support_knowledge_dense_index_runtime import SupportKnowledgeDenseIndexRuntime
    from app.application.retrieval.hybrid_support_knowledge_chunk_retriever import HybridSupportKnowledgeChunkRetriever
    from app.application.retrieval.reranking_support_knowledge_chunk_retriever import RerankingSupportKnowledgeChunkRetriever
    from app.infrastructure.persistence.json_file_dense_support_knowledge_index_store import JsonFileDenseSupportKnowledgeIndexStore
    from app.infrastructure.models.qwen_openai_compatible_support_knowledge_reranker import QwenOpenAICompatibleSupportKnowledgeReranker
    settings = load_settings()
    if not settings.embedding_model_api_key or not settings.reranker_model_api_key:
        raise ValueError("real embedding and reranker credentials are required")
    config = {
        "embedding_model": settings.embedding_model_name, "embedding_revision": settings.embedding_model_revision,
        "dimension": settings.embedding_model_dimension, "reranker_model": settings.reranker_model_name,
        "reranker_revision": settings.reranker_model_revision,
        "hybrid_candidate_k": settings.hybrid_candidate_k, "rrf_rank_constant": settings.hybrid_rank_constant,
        "reranker_candidate_k": settings.reranker_candidate_k, "ranking_depth": 10,
        "embedding_endpoint": settings.embedding_model_base_url,
        "reranker_endpoint": settings.reranker_model_base_url,
        "model_revision_kind": "configured labels; hosted weights are not independently pinned",
        "retrieval_code_sha256": {
            name: digest((Path("app") / name).read_bytes()) for name in (
                "application/support_knowledge_chunk_retrieval.py",
                "application/support_knowledge_retrieval.py",
                "application/dense_support_knowledge_chunk_retrieval.py",
                "application/hybrid_support_knowledge_chunk_retriever.py",
                "application/reciprocal_rank_fusion.py",
                "application/reranking_support_knowledge_chunk_retriever.py",
                "infrastructure/qwen_openai_compatible_text_embedder.py",
                "infrastructure/qwen_openai_compatible_support_knowledge_reranker.py",
            )
        },
    }
    if settings.reranker_candidate_k != 10:
        raise ValueError("frozen benchmark requires ten reranker candidates")
    run_key = digest(json.dumps({"dataset": fixture_hash, "config": config}, sort_keys=True).encode())
    run_cache = cache / run_key
    run_cache.mkdir(parents=True, exist_ok=True)
    corpus, dataset, metadata = build_fixture_corpus(fixture)
    golden_path = run_cache / "judgments.json"
    atomic_json(golden_path, dataset)
    embedder = QueryCachingEmbedder(build_support_knowledge_text_embedder(
        settings, httpx.Client(timeout=settings.embedding_model_timeout_seconds, trust_env=False)), run_cache / "queries")
    runtime = SupportKnowledgeDenseIndexRuntime(corpus, embedder,
        JsonFileDenseSupportKnowledgeIndexStore(run_cache / "dense-index.json"))
    reranker = QwenOpenAICompatibleSupportKnowledgeReranker(
        base_url=settings.reranker_model_base_url, api_key=settings.reranker_model_api_key,
        model=settings.reranker_model_name, revision=settings.reranker_model_revision,
        http_client=httpx.Client(timeout=settings.reranker_model_timeout_seconds, trust_env=False))
    try:
        started = perf_counter()
        runtime.prepare()
        chunks = {chunk.chunk_id: chunk for chunk in corpus.retrieval_snapshot()[2]}
        bm25 = CachedSearcher("bm25", LexicalSupportKnowledgeChunkRetriever(tuple(chunks.values())), chunks, run_cache)
        dense = CachedSearcher("dense", runtime, chunks, run_cache)
        # Hybrid needs twenty candidates from each branch; use the project retrievers,
        # not the ten-result evaluation cache. Query embeddings remain shared/cached.
        hybrid_delegate = HybridSupportKnowledgeChunkRetriever(
            bm25.delegate, runtime, candidate_k=settings.hybrid_candidate_k, rank_constant=settings.hybrid_rank_constant)
        hybrid = CachedSearcher("hybrid", hybrid_delegate, chunks, run_cache)
        reranked = CachedSearcher("hybrid_rerank", RerankingSupportKnowledgeChunkRetriever(
            hybrid, reranker, candidate_k=10, allow_degraded=False), chunks, run_cache)
        retrievers = OrderedDict(bm25=bm25, dense=dense, hybrid=hybrid, hybrid_rerank=reranked)
        report = asdict(run_retrieval_comparison_evaluation(
            corpus=corpus, retrievers=retrievers, dataset_path=golden_path, top_k=5))
        for variant in report["variants"]:
            delegate = retrievers[variant["variant"]].delegate
            variant["retriever_identity"] = f"{type(delegate).__module__}.{type(delegate).__qualname__}"
        report.update({
            "status": "complete", "benchmark_sha256": fixture_hash,
            "sources_manifest_sha256": digest(manifest_path.read_bytes()),
            "annotation_status": fixture["annotation_status"], "human_reviewed": False,
            "scope": fixture["scope"], "sources": len(fixture["sources"]),
            "evidence_units": len(chunks), "queries": len(metadata), "config": config,
            "elapsed_seconds": round(perf_counter() - started, 3),
            "case_metadata": metadata,
            "strata": {kind: {variant["variant"]: aggregate([
                row for row in variant["cases"] if metadata[row["case_id"]]["query_type"] == kind])
                for variant in report["variants"]} for kind in QUERY_TYPES},
            "paired_95ci": clustered_intervals(report["variants"], metadata),
            "citation_boundary": "all chunks have a verified source URL and section; generated-answer citation correctness was not measured",
        })
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(json.dumps({"queries": report["queries"], "evidence_units": len(chunks),
            "variants": [{k: v for k, v in variant.items() if k != "cases"} for variant in report["variants"]]}, indent=2))
    finally:
        runtime.close()
        reranker.close()


if __name__ == "__main__":
    main()
