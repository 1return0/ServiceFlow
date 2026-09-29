"""Application composition helpers.

This module decides which concrete infrastructure implementation is used for
an application protocol.  HTTP routes and graphs stay unaware of whether the
planner is rule-based or model-backed.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi import FastAPI

from app.application.model_ticket_lookup_planner import ModelTicketLookupPlanner
from app.application.model_triage_planner import ModelTriagePlanner
from app.application.handoff_guard import CampusRiskHandoffGuard
from app.application.fallback_triage_planner import FallbackTriagePlanner
from app.application.model_grounded_support_knowledge_answering import (
    ModelGroundedSupportKnowledgeAnswerService,
)
from app.application.support_knowledge_answering import (
    ExtractiveSupportKnowledgeAnswerService,
    SupportKnowledgeAnswerProvider,
)
from app.application.refreshable_support_knowledge_chunk_retriever import (
    RefreshableSupportKnowledgeChunkRetriever,
)
from app.application.refreshable_hybrid_support_knowledge_searcher import (
    RefreshableHybridSupportKnowledgeSearcher,
)
from app.application.reranking_support_knowledge_searcher import (
    RerankingSupportKnowledgeSearcher,
)
from app.application.controlled_secondary_support_knowledge_searcher import (
    ControlledSecondarySupportKnowledgeSearcher,
)
from app.application.model_support_knowledge_query_rewriter import (
    ModelSupportKnowledgeQueryRewriter,
)
from app.application.support_knowledge_dense_index_runtime import (
    SupportKnowledgeDenseIndexRuntime,
)
from app.application.support_knowledge_tool import SupportKnowledgeAnswerTool
from app.application.knowledge_specialist_agent import KnowledgeSpecialistAgent
from app.application.support_knowledge_document_parsing_service import (
    SupportKnowledgeDocumentParsingService,
)
from app.application.support_knowledge_ingestion_service import (
    SupportKnowledgeIngestionService,
)
from app.application.knowledge_import_access_policy import (
    KnowledgeImportAccessPolicy,
)
from app.application.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssembler,
)
from app.application.fragment_aware_support_knowledge_chunker import (
    FragmentAwareSupportKnowledgeChunker,
)
from app.application.support_knowledge_parser_registry import (
    SupportKnowledgeParserRegistry,
)
from app.application.ticket_lookup_tool import TicketLookupTool
from app.application.ticket_specialist_agent import TicketSpecialistAgent
from app.application.notification_specialist_agent import NotificationSpecialistAgent
from app.application.notification_summary_tool import NotificationSummaryTool
from app.application.human_handoff_task_tool import HumanHandoffTaskTool
from app.application.workflows.campus_support_triage_graph import (
    CampusSupportTriageGraph,
)
from app.config import Settings
from app.domain.ticket_lookup_plan import (
    RuleBasedTicketLookupPlanner,
    TicketLookupPlanner,
)
from app.domain.triage_plan import RuleBasedTriagePlanner
from app.domain.triage_plan import TriagePlanner
from app.infrastructure.business_client import BusinessServiceClient
from app.infrastructure.retry_policy import BoundedRetryPolicy
from app.infrastructure.qwen_openai_planner_model import (
    QwenOpenAICompatiblePlannerModel,
)
from app.infrastructure.qwen_support_knowledge_answer_generator import (
    QwenSupportKnowledgeAnswerGenerator,
)
from app.infrastructure.qwen_openai_compatible_text_embedder import (
    QwenOpenAICompatibleTextEmbedder,
)
from app.infrastructure.qwen_openai_compatible_support_knowledge_reranker import (
    QwenOpenAICompatibleSupportKnowledgeReranker,
)
from app.infrastructure.json_support_knowledge_catalog import (
    JsonSupportKnowledgeCatalog,
)
from app.infrastructure.html_support_knowledge_artifact_parser import (
    HtmlSupportKnowledgeArtifactParser,
)
from app.infrastructure.pdf_support_knowledge_artifact_parser import (
    PdfSupportKnowledgeArtifactParser,
)
from app.infrastructure.pdf_ocr_fallback_support_knowledge_artifact_parser import (
    PdfOcrFallbackSupportKnowledgeArtifactParser,
)
from app.infrastructure.pdf_page_rendering import (
    PdfPageRasterizationPlanner,
    PdfPageRasterizationSettings,
)
from app.infrastructure.pdfium_pdf_page_renderer import PdfiumPdfPageRenderer
from app.infrastructure.openai_compatible_vision_ocr_text_extractor import (
    OpenAiCompatibleVisionOcrTextExtractor,
)
from app.infrastructure.docx_support_knowledge_artifact_parser import (
    DocxSupportKnowledgeArtifactParser,
)
from app.infrastructure.pptx_support_knowledge_artifact_parser import (
    PptxSupportKnowledgeArtifactParser,
)
from app.infrastructure.xlsx_support_knowledge_artifact_parser import (
    XlsxSupportKnowledgeArtifactParser,
)
from app.infrastructure.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
)
from app.infrastructure.json_file_current_support_knowledge_corpus import (
    JsonFileCurrentSupportKnowledgeCorpus,
)
from app.infrastructure.json_file_dense_support_knowledge_index_store import (
    JsonFileDenseSupportKnowledgeIndexStore,
)
from app.domain.support_knowledge import CurrentSupportKnowledgeCorpus


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SUPPORT_KNOWLEDGE_CATALOG_PATH = (
    _PROJECT_ROOT / "data" / "support-knowledge" / "demo-campus-support-v1.json"
)
_SUPPORT_KNOWLEDGE_ARTIFACT_ROOT = _PROJECT_ROOT / "data" / "support-knowledge" / "artifacts"
_SUPPORT_KNOWLEDGE_CURRENT_CORPUS_PATH = (
    _PROJECT_ROOT / "data" / "support-knowledge" / "current-corpus.json"
)
_SUPPORT_KNOWLEDGE_DENSE_INDEX_PATH = (
    _PROJECT_ROOT / "data" / "support-knowledge" / "dense-index.json"
)


@dataclass
class TicketLookupPlannerRuntime:
    planner: TicketLookupPlanner

    def close(self) -> None:
        close = getattr(self.planner, "close", None)
        if callable(close):
            close()


@dataclass
class CampusSupportTriageRuntime:
    graph: CampusSupportTriageGraph
    planner: TriagePlanner
    http_client: httpx.Client

    def close(self) -> None:
        self.http_client.close()
        close = getattr(self.planner, "close", None)
        if callable(close):
            close()


def build_ticket_lookup_planner(settings: Settings) -> TicketLookupPlanner:
    """Build the selected planner without exposing provider details to routes."""
    if not settings.planner_model_enabled:
        return RuleBasedTicketLookupPlanner()

    return ModelTicketLookupPlanner(_build_qwen_completion_model(settings))


def build_triage_planner(settings: Settings) -> TriagePlanner:
    if not settings.triage_model_enabled:
        return RuleBasedTriagePlanner()
    return FallbackTriagePlanner(
        ModelTriagePlanner(_build_qwen_completion_model(settings)),
        RuleBasedTriagePlanner(),
    )


def build_support_knowledge_answer_service(
    settings: Settings,
    current_corpus: CurrentSupportKnowledgeCorpus,
    dense_index_runtime: SupportKnowledgeDenseIndexRuntime | None = None,
) -> SupportKnowledgeAnswerProvider:
    if settings.reranker_enabled and not settings.hybrid_retrieval_enabled:
        raise ValueError("hybrid retrieval must be enabled when reranker is enabled")
    if settings.query_rewrite_enabled and not settings.controlled_secondary_search_enabled:
        raise ValueError(
            "controlled secondary search must be enabled when query rewrite is enabled"
        )
    if settings.hybrid_retrieval_enabled:
        if dense_index_runtime is None:
            raise ValueError(
                "dense index runtime is required when hybrid retrieval is enabled"
            )
        retriever = RefreshableHybridSupportKnowledgeSearcher(
            current_corpus,
            dense_index_runtime,
            candidate_k=settings.hybrid_candidate_k,
            rank_constant=settings.hybrid_rank_constant,
        )
        if settings.reranker_enabled:
            retriever = RerankingSupportKnowledgeSearcher(
                retriever,
                build_support_knowledge_reranker(settings),
                candidate_k=settings.reranker_candidate_k,
            )
    else:
        retriever = RefreshableSupportKnowledgeChunkRetriever(current_corpus)
    if settings.controlled_secondary_search_enabled:
        retriever = ControlledSecondarySupportKnowledgeSearcher(
            retriever,
            minimum_evidence_count=settings.secondary_search_minimum_evidence_count,
            secondary_top_k=settings.secondary_search_top_k,
            query_rewriter=(
                ModelSupportKnowledgeQueryRewriter(_build_qwen_completion_model(settings))
                if settings.query_rewrite_enabled
                else None
            ),
        )
    if settings.knowledge_answer_generation_enabled:
        completion_model = _build_qwen_completion_model(settings)
        return ModelGroundedSupportKnowledgeAnswerService(
            retriever,
            QwenSupportKnowledgeAnswerGenerator(completion_model),
        )
    return ExtractiveSupportKnowledgeAnswerService(retriever)


def build_support_knowledge_reranker(
    settings: Settings,
) -> QwenOpenAICompatibleSupportKnowledgeReranker:
    if not settings.reranker_model_base_url:
        raise ValueError("SERVICEFLOW_RERANKER_MODEL_BASE_URL is required")
    if not settings.reranker_model_api_key:
        raise ValueError(
            f"{settings.reranker_model_api_key_environment_variable} is required"
        )
    return QwenOpenAICompatibleSupportKnowledgeReranker(
        base_url=settings.reranker_model_base_url,
        api_key=settings.reranker_model_api_key,
        model=settings.reranker_model_name,
        revision=settings.reranker_model_revision,
        http_client=httpx.Client(timeout=settings.reranker_model_timeout_seconds),
    )


def build_support_knowledge_document_parsing_service(
    artifact_root: Path,
    settings: Settings | None = None,
) -> SupportKnowledgeDocumentParsingService:
    selected_settings = settings or Settings()
    pdf_parser = PdfSupportKnowledgeArtifactParser(artifact_root)
    if selected_settings.ocr_enabled:
        pdf_parser = _build_pdf_ocr_fallback_parser(
            selected_settings,
            artifact_root,
        )
    return SupportKnowledgeDocumentParsingService(
        SupportKnowledgeParserRegistry(
            (
                HtmlSupportKnowledgeArtifactParser(artifact_root),
                pdf_parser,
                DocxSupportKnowledgeArtifactParser(artifact_root),
                XlsxSupportKnowledgeArtifactParser(artifact_root),
                PptxSupportKnowledgeArtifactParser(artifact_root),
            )
        )
    )


def build_current_support_knowledge_corpus() -> JsonFileCurrentSupportKnowledgeCorpus:
    return JsonFileCurrentSupportKnowledgeCorpus(
        JsonSupportKnowledgeCatalog(_SUPPORT_KNOWLEDGE_CATALOG_PATH).list_articles(),
        _SUPPORT_KNOWLEDGE_CURRENT_CORPUS_PATH,
    )


def build_support_knowledge_ingestion_service(
    current_corpus: CurrentSupportKnowledgeCorpus,
    settings: Settings | None = None,
) -> SupportKnowledgeIngestionService:
    artifact_root = _SUPPORT_KNOWLEDGE_ARTIFACT_ROOT
    return SupportKnowledgeIngestionService(
        FileSystemSupportKnowledgeArtifactStore(artifact_root),
        build_support_knowledge_document_parsing_service(artifact_root, settings),
        SupportKnowledgeArticleAssembler(),
        current_corpus,
        FragmentAwareSupportKnowledgeChunker(),
    )


def build_campus_support_triage_runtime(
    settings: Settings,
    support_knowledge_answer_service: SupportKnowledgeAnswerProvider,
) -> CampusSupportTriageRuntime:
    http_client = httpx.Client(timeout=settings.business_service_timeout_seconds)
    business_service_client = build_business_service_client(settings, http_client)
    ticket_specialist = TicketSpecialistAgent(TicketLookupTool(business_service_client))
    planner = build_triage_planner(settings)
    graph = CampusSupportTriageGraph(
        planner,
        ticket_specialist,
        KnowledgeSpecialistAgent(
            SupportKnowledgeAnswerTool(support_knowledge_answer_service)
        ),
        CampusRiskHandoffGuard(),
        NotificationSpecialistAgent(NotificationSummaryTool(business_service_client)),
        HumanHandoffTaskTool(business_service_client),
    )
    return CampusSupportTriageRuntime(
        graph=graph,
        planner=planner,
        http_client=http_client,
    )


def build_business_service_client(
    settings: Settings,
    http_client: httpx.Client,
) -> BusinessServiceClient:
    return BusinessServiceClient(
        settings.business_service_base_url,
        http_client,
        retry_policy=BoundedRetryPolicy(
            max_attempts=settings.business_service_read_max_attempts,
            initial_backoff_seconds=(
                settings.business_service_read_initial_backoff_seconds
            ),
        ),
    )


def _build_qwen_completion_model(
    settings: Settings,
) -> QwenOpenAICompatiblePlannerModel:
    if not settings.planner_model_base_url:
        raise ValueError("SERVICEFLOW_PLANNER_MODEL_BASE_URL is required")
    if not settings.planner_model_api_key:
        raise ValueError(
            f"{settings.planner_model_api_key_environment_variable} is required"
        )
    return QwenOpenAICompatiblePlannerModel(
        base_url=settings.planner_model_base_url,
        api_key=settings.planner_model_api_key,
        model=settings.planner_model_name,
        http_client=httpx.Client(timeout=settings.planner_model_timeout_seconds),
    )


def build_support_knowledge_text_embedder(
    settings: Settings,
    http_client: httpx.Client,
) -> QwenOpenAICompatibleTextEmbedder:
    """Build the real embedding adapter; lifecycle ownership stays with caller."""
    if not settings.embedding_model_base_url:
        raise ValueError("SERVICEFLOW_EMBEDDING_MODEL_BASE_URL is required")
    if not settings.embedding_model_api_key:
        raise ValueError(
            f"{settings.embedding_model_api_key_environment_variable} is required"
        )
    return QwenOpenAICompatibleTextEmbedder(
        base_url=settings.embedding_model_base_url,
        api_key=settings.embedding_model_api_key,
        model=settings.embedding_model_name,
        revision=settings.embedding_model_revision,
        dimension=settings.embedding_model_dimension,
        batch_size=settings.embedding_model_batch_size,
        http_client=http_client,
    )


def _build_pdf_ocr_fallback_parser(
    settings: Settings,
    artifact_root: Path,
) -> PdfOcrFallbackSupportKnowledgeArtifactParser:
    if not settings.ocr_model_base_url:
        raise ValueError("SERVICEFLOW_OCR_MODEL_BASE_URL is required")
    if not settings.ocr_model_api_key:
        raise ValueError(f"{settings.ocr_model_api_key_environment_variable} is required")
    renderer = PdfiumPdfPageRenderer(
        artifact_root,
        PdfPageRasterizationPlanner(
            PdfPageRasterizationSettings(
                dpi=settings.ocr_render_dpi,
                max_page_pixels=settings.ocr_max_page_pixels,
            )
        ),
    )
    extractor = OpenAiCompatibleVisionOcrTextExtractor(
        base_url=settings.ocr_model_base_url,
        api_key=settings.ocr_model_api_key,
        model=settings.ocr_model_name,
        page_renderer=renderer,
        http_client=httpx.Client(timeout=settings.ocr_model_timeout_seconds),
    )
    return PdfOcrFallbackSupportKnowledgeArtifactParser(
        PdfSupportKnowledgeArtifactParser(artifact_root),
        extractor,
    )


def build_application_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Validate the write-side import boundary before assembling any runtime.
        app.state.knowledge_import_access_policy = (
            KnowledgeImportAccessPolicy.from_settings(settings)
        )
        runtime = TicketLookupPlannerRuntime(
            planner=build_ticket_lookup_planner(settings),
        )
        app.state.ticket_lookup_planner = runtime.planner
        app.state.current_support_knowledge_corpus = (
            build_current_support_knowledge_corpus()
        )
        dense_index_runtime: SupportKnowledgeDenseIndexRuntime | None = None
        if settings.dense_retrieval_enabled:
            dense_index_runtime = SupportKnowledgeDenseIndexRuntime(
                app.state.current_support_knowledge_corpus,
                build_support_knowledge_text_embedder(
                    settings,
                    httpx.Client(timeout=settings.embedding_model_timeout_seconds),
                ),
                JsonFileDenseSupportKnowledgeIndexStore(
                    _SUPPORT_KNOWLEDGE_DENSE_INDEX_PATH
                ),
            )
            dense_index_runtime.prepare()
            app.state.support_knowledge_dense_index_runtime = dense_index_runtime
        app.state.support_knowledge_answer_service = (
            build_support_knowledge_answer_service(
                settings,
                app.state.current_support_knowledge_corpus,
                dense_index_runtime,
            )
        )
        app.state.support_knowledge_ingestion_service = (
            build_support_knowledge_ingestion_service(
                app.state.current_support_knowledge_corpus,
                settings,
            )
        )
        app.state.campus_support_triage_runtime = (
            build_campus_support_triage_runtime(
                settings,
                app.state.support_knowledge_answer_service,
            )
        )
        try:
            yield
        finally:
            triage_runtime = app.state.campus_support_triage_runtime
            del app.state.campus_support_triage_runtime
            del app.state.ticket_lookup_planner
            knowledge_service = app.state.support_knowledge_answer_service
            del app.state.support_knowledge_answer_service
            ingestion_service = app.state.support_knowledge_ingestion_service
            del app.state.support_knowledge_ingestion_service
            if dense_index_runtime is not None:
                del app.state.support_knowledge_dense_index_runtime
                dense_index_runtime.close()
            del app.state.current_support_knowledge_corpus
            del app.state.knowledge_import_access_policy
            runtime.close()
            triage_runtime.close()
            close = getattr(knowledge_service, "close", None)
            if callable(close):
                close()
            ingestion_service.close()

    return lifespan
