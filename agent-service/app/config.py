from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
# Tests and deterministic local tooling must not accidentally consume a
# developer's real model configuration. Production/local startup simply omits
# this switch and continues to load .env as before.
if os.getenv("PYTHON_DOTENV_DISABLED", "false").strip().casefold() not in {
    "1",
    "true",
    "yes",
}:
    load_dotenv(_ENV_FILE, override=True)


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "eduops-agent"
    version: str = "0.1.0"
    environment: str = "development"
    business_service_base_url: str = "http://127.0.0.1:8120"
    business_service_timeout_seconds: float = 3.0
    business_service_read_max_attempts: int = 2
    business_service_read_initial_backoff_seconds: float = 0.1
    memory_postgres_dsn: str | None = None
    planner_model_enabled: bool = False
    triage_model_enabled: bool = False
    knowledge_answer_generation_enabled: bool = False
    knowledge_import_enabled: bool = False
    knowledge_import_admin_token: str | None = None
    ocr_enabled: bool = False
    ocr_model_base_url: str | None = None
    ocr_model_name: str = "qwen3.5-ocr"
    ocr_model_api_key_environment_variable: str = "DASHSCOPE_API_KEY"
    ocr_model_api_key: str | None = None
    ocr_model_timeout_seconds: float = 60.0
    ocr_render_dpi: int = 144
    ocr_max_page_pixels: int = 8_000_000
    planner_model_base_url: str | None = None
    planner_model_name: str = "qwen-plus"
    planner_model_api_key_environment_variable: str = "DASHSCOPE_API_KEY"
    planner_model_api_key: str | None = None
    planner_model_timeout_seconds: float = 30.0
    embedding_model_base_url: str | None = None
    embedding_model_name: str = "qwen3.7-text-embedding-flash"
    embedding_model_revision: str = "qwen3.7-text-embedding-flash-2026-09"
    embedding_model_api_key_environment_variable: str = "DASHSCOPE_API_KEY"
    embedding_model_api_key: str | None = None
    embedding_model_timeout_seconds: float = 30.0
    embedding_model_dimension: int = 1024
    embedding_model_batch_size: int = 20
    dense_retrieval_enabled: bool = False
    hybrid_retrieval_enabled: bool = False
    hybrid_candidate_k: int = 20
    hybrid_rank_constant: int = 60
    reranker_enabled: bool = False
    reranker_model_base_url: str | None = None
    reranker_model_name: str = "qwen3-rerank"
    reranker_model_revision: str = "qwen3-rerank-2026-09"
    reranker_model_api_key_environment_variable: str = "DASHSCOPE_API_KEY"
    reranker_model_api_key: str | None = None
    reranker_model_timeout_seconds: float = 30.0
    reranker_candidate_k: int = 10
    controlled_secondary_search_enabled: bool = False
    secondary_search_minimum_evidence_count: int = 2
    secondary_search_top_k: int = 6
    query_rewrite_enabled: bool = False


def load_settings() -> Settings:
    planner_api_key_environment_variable = os.getenv(
        "SERVICEFLOW_PLANNER_MODEL_API_KEY_ENV",
        "DASHSCOPE_API_KEY",
    ).strip()
    ocr_api_key_environment_variable = os.getenv(
        "SERVICEFLOW_OCR_MODEL_API_KEY_ENV",
        "DASHSCOPE_API_KEY",
    ).strip()
    embedding_api_key_environment_variable = os.getenv(
        "SERVICEFLOW_EMBEDDING_MODEL_API_KEY_ENV",
        "DASHSCOPE_API_KEY",
    ).strip()
    reranker_api_key_environment_variable = os.getenv(
        "SERVICEFLOW_RERANKER_MODEL_API_KEY_ENV",
        "DASHSCOPE_API_KEY",
    ).strip()
    return Settings(
        environment=os.getenv(
            "SERVICEFLOW_ENV",
            "development",
        ),
        business_service_base_url=os.getenv(
            "SERVICEFLOW_BUSINESS_BASE_URL",
            "http://127.0.0.1:8120",
        ).rstrip("/"),
        business_service_timeout_seconds=float(
            os.getenv("SERVICEFLOW_BUSINESS_TIMEOUT_SECONDS", "3.0")
        ),
        business_service_read_max_attempts=int(
            os.getenv("SERVICEFLOW_BUSINESS_READ_MAX_ATTEMPTS", "2")
        ),
        business_service_read_initial_backoff_seconds=float(
            os.getenv(
                "SERVICEFLOW_BUSINESS_READ_INITIAL_BACKOFF_SECONDS",
                "0.1",
            )
        ),
        memory_postgres_dsn=_read_optional(
            os.getenv("SERVICEFLOW_MEMORY_POSTGRES_DSN")
        ),
        planner_model_enabled=_read_bool(
            os.getenv("SERVICEFLOW_PLANNER_MODEL_ENABLED", "false")
        ),
        triage_model_enabled=_read_bool(
            os.getenv("SERVICEFLOW_TRIAGE_MODEL_ENABLED", "false")
        ),
        knowledge_answer_generation_enabled=_read_bool(
            os.getenv("SERVICEFLOW_KNOWLEDGE_ANSWER_GENERATION_ENABLED", "false")
        ),
        knowledge_import_enabled=_read_bool(
            os.getenv("SERVICEFLOW_KNOWLEDGE_IMPORT_ENABLED", "false")
        ),
        knowledge_import_admin_token=_read_optional(
            os.getenv("SERVICEFLOW_KNOWLEDGE_IMPORT_ADMIN_TOKEN")
        ),
        ocr_enabled=_read_bool(os.getenv("SERVICEFLOW_OCR_ENABLED", "false")),
        ocr_model_base_url=_read_optional(
            os.getenv("SERVICEFLOW_OCR_MODEL_BASE_URL")
        ),
        ocr_model_name=os.getenv("SERVICEFLOW_OCR_MODEL_NAME", "qwen3.5-ocr"),
        ocr_model_api_key_environment_variable=ocr_api_key_environment_variable,
        ocr_model_api_key=_read_optional(
            os.getenv(ocr_api_key_environment_variable)
        ),
        ocr_model_timeout_seconds=float(
            os.getenv("SERVICEFLOW_OCR_MODEL_TIMEOUT_SECONDS", "60")
        ),
        ocr_render_dpi=int(os.getenv("SERVICEFLOW_OCR_RENDER_DPI", "144")),
        ocr_max_page_pixels=int(
            os.getenv("SERVICEFLOW_OCR_MAX_PAGE_PIXELS", "8000000")
        ),
        planner_model_base_url=_read_optional(
            os.getenv("SERVICEFLOW_PLANNER_MODEL_BASE_URL")
        ),
        planner_model_name=os.getenv(
            "SERVICEFLOW_PLANNER_MODEL_NAME",
            "qwen-plus",
        ),
        planner_model_api_key_environment_variable=(
            planner_api_key_environment_variable
        ),
        planner_model_api_key=_read_optional(
            os.getenv(planner_api_key_environment_variable)
        ),
        planner_model_timeout_seconds=float(
            os.getenv("SERVICEFLOW_PLANNER_MODEL_TIMEOUT_SECONDS", "30")
        ),
        embedding_model_base_url=_read_optional(
            os.getenv("SERVICEFLOW_EMBEDDING_MODEL_BASE_URL")
        ),
        embedding_model_name=os.getenv(
            "SERVICEFLOW_EMBEDDING_MODEL_NAME",
            "qwen3.7-text-embedding-flash",
        ),
        embedding_model_revision=os.getenv(
            "SERVICEFLOW_EMBEDDING_MODEL_REVISION",
            "qwen3.7-text-embedding-flash-2026-09",
        ),
        embedding_model_api_key_environment_variable=(
            embedding_api_key_environment_variable
        ),
        embedding_model_api_key=_read_optional(
            os.getenv(embedding_api_key_environment_variable)
        ),
        embedding_model_timeout_seconds=float(
            os.getenv("SERVICEFLOW_EMBEDDING_MODEL_TIMEOUT_SECONDS", "30")
        ),
        embedding_model_dimension=int(
            os.getenv("SERVICEFLOW_EMBEDDING_MODEL_DIMENSION", "1024")
        ),
        embedding_model_batch_size=int(
            os.getenv("SERVICEFLOW_EMBEDDING_MODEL_BATCH_SIZE", "20")
        ),
        dense_retrieval_enabled=_read_bool(
            os.getenv("SERVICEFLOW_DENSE_RETRIEVAL_ENABLED", "false")
        ),
        hybrid_retrieval_enabled=_read_bool(
            os.getenv("SERVICEFLOW_HYBRID_RETRIEVAL_ENABLED", "false")
        ),
        hybrid_candidate_k=int(os.getenv("SERVICEFLOW_HYBRID_CANDIDATE_K", "20")),
        hybrid_rank_constant=int(os.getenv("SERVICEFLOW_HYBRID_RANK_CONSTANT", "60")),
        reranker_enabled=_read_bool(os.getenv("SERVICEFLOW_RERANKER_ENABLED", "false")),
        reranker_model_base_url=_read_optional(
            os.getenv("SERVICEFLOW_RERANKER_MODEL_BASE_URL")
        ),
        reranker_model_name=os.getenv(
            "SERVICEFLOW_RERANKER_MODEL_NAME",
            "qwen3-rerank",
        ),
        reranker_model_revision=os.getenv(
            "SERVICEFLOW_RERANKER_MODEL_REVISION",
            "qwen3-rerank-2026-09",
        ),
        reranker_model_api_key_environment_variable=reranker_api_key_environment_variable,
        reranker_model_api_key=_read_optional(
            os.getenv(reranker_api_key_environment_variable)
        ),
        reranker_model_timeout_seconds=float(
            os.getenv("SERVICEFLOW_RERANKER_MODEL_TIMEOUT_SECONDS", "30")
        ),
        reranker_candidate_k=int(os.getenv("SERVICEFLOW_RERANKER_CANDIDATE_K", "10")),
        controlled_secondary_search_enabled=_read_bool(
            os.getenv("SERVICEFLOW_CONTROLLED_SECONDARY_SEARCH_ENABLED", "false")
        ),
        secondary_search_minimum_evidence_count=int(
            os.getenv("SERVICEFLOW_SECONDARY_SEARCH_MINIMUM_EVIDENCE_COUNT", "2")
        ),
        secondary_search_top_k=int(
            os.getenv("SERVICEFLOW_SECONDARY_SEARCH_TOP_K", "6")
        ),
        query_rewrite_enabled=_read_bool(
            os.getenv("SERVICEFLOW_QUERY_REWRITE_ENABLED", "false")
        ),
    )


def _read_optional(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _read_bool(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("boolean configuration value must be true or false")
