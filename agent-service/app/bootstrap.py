"""Application composition helpers.

This module decides which concrete infrastructure implementation is used for
an application protocol.  HTTP routes and graphs stay unaware of whether the
planner is rule-based or model-backed.
"""

from contextlib import asynccontextmanager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi import FastAPI

from app.application.model_ticket_lookup_planner import ModelTicketLookupPlanner
from app.application.agent_harness import HarnessedCompletionModel
from app.application.model_triage_planner import ModelTriagePlanner
from app.application.agent_tool_planning import AgentToolDefinition
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
from app.application.trusted_subject import (
    JavaTrustedSubjectResolver,
    build_serviceflow_thread_id,
)
from app.application.long_term_memory import (
    LongTermMemoryEntry,
    LongTermMemoryService,
)
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
from app.infrastructure.postgres_checkpointer import open_postgres_checkpointer
from app.infrastructure.postgres_long_term_memory_store import (
    open_postgres_long_term_memory_store,
)
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
    trusted_subject_resolver: JavaTrustedSubjectResolver
    memory_service: LongTermMemoryService | None = None

    def invoke(
        self,
        *,
        user_query: str,
        authorization: str | None,
    ) -> dict[str, object]:
        owner_id = None
        preferences: dict[str, str] = {}
        if authorization is not None:
            owner_id = self.trusted_subject_resolver.resolve(
                authorization
            ).owner_id
            preferences = {
                entry.preference_key: entry.preference_value
                for entry in self.list_preferences(owner_id=owner_id)
            }
        return self.graph.invoke(
            user_query=user_query,
            authorization=authorization,
            owner_id=owner_id,
            thread_id=(
                build_serviceflow_thread_id(owner_id)
                if owner_id is not None
                else None
            ),
            preferences=preferences,
        )

    def resolve_owner_id(self, authorization: str | None) -> str:
        return self.trusted_subject_resolver.resolve(authorization).owner_id

    def get_authenticated_conversation_turns(
        self,
        *,
        authorization: str | None,
    ) -> tuple[str, ...]:
        owner_id = self.resolve_owner_id(authorization)
        return self.graph.get_conversation_turns(
            thread_id=build_serviceflow_thread_id(owner_id)
        )

    def clear_authenticated_conversation(
        self,
        *,
        authorization: str | None,
    ) -> bool:
        owner_id = self.resolve_owner_id(authorization)
        return self.graph.clear_conversation_thread(
            thread_id=build_serviceflow_thread_id(owner_id)
        )

    def remember_preference(
        self,
        *,
        authorization: str | None,
        preference_key: str,
        preference_value: str,
        user_consented: bool,
    ) -> LongTermMemoryEntry:
        return self._require_memory_service().remember_preference(
            owner_id=self.resolve_owner_id(authorization),
            preference_key=preference_key,
            preference_value=preference_value,
            user_consented=user_consented,
        )

    def list_preferences(
        self,
        *,
        owner_id: str,
    ) -> tuple[LongTermMemoryEntry, ...]:
        if self.memory_service is None:
            return ()
        return self.memory_service.list_preferences(owner_id=owner_id)

    def list_authenticated_preferences(
        self,
        *,
        authorization: str | None,
    ) -> tuple[LongTermMemoryEntry, ...]:
        return self.list_preferences(owner_id=self.resolve_owner_id(authorization))

    def forget_preference(
        self,
        *,
        authorization: str | None,
        preference_key: str,
    ) -> bool:
        return self._require_memory_service().forget_preference(
            owner_id=self.resolve_owner_id(authorization),
            preference_key=preference_key,
        )

    def forget_all_preferences(self, *, authorization: str | None) -> int:
        return self._require_memory_service().forget_all_preferences(
            owner_id=self.resolve_owner_id(authorization)
        )

    def _require_memory_service(self) -> LongTermMemoryService:
        if self.memory_service is None:
            raise RuntimeError("long-term memory is not prepared")
        return self.memory_service

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


def build_triage_planner(
    settings: Settings, *, tools: tuple[AgentToolDefinition, ...] | None = None,
) -> TriagePlanner:
    if not settings.triage_model_enabled:
        return RuleBasedTriagePlanner()
    return FallbackTriagePlanner(
        ModelTriagePlanner(
            HarnessedCompletionModel(
                _build_qwen_completion_model(settings),
                operation_name="triage_planner_model",
            ),
            tools=tools,
        ),
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
                ModelSupportKnowledgeQueryRewriter(
                    HarnessedCompletionModel(
                        _build_qwen_completion_model(settings),
                        operation_name="support_knowledge_query_rewriter_model",
                    )
                )
                if settings.query_rewrite_enabled
                else None
            ),
        )
    if settings.knowledge_answer_generation_enabled:
        completion_model = HarnessedCompletionModel(
            _build_qwen_completion_model(settings),
            operation_name="support_knowledge_answer_model",
        )
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
        http_client=httpx.Client(timeout=settings.reranker_model_timeout_seconds, trust_env=settings.http_trust_env),
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
    *,
    checkpointer: object | None = None,
    memory_service: LongTermMemoryService | None = None,
) -> CampusSupportTriageRuntime:
    http_client = httpx.Client(timeout=settings.business_service_timeout_seconds, trust_env=settings.http_trust_env)
    business_service_client = build_business_service_client(settings, http_client)
    ticket_tool = TicketLookupTool(business_service_client)
    knowledge_tool = SupportKnowledgeAnswerTool(support_knowledge_answer_service)
    notification_tool = NotificationSummaryTool(business_service_client)
    handoff_tool = HumanHandoffTaskTool(business_service_client)
    ticket_specialist = TicketSpecialistAgent(ticket_tool)
    planner = build_triage_planner(settings, tools=tuple(
        AgentToolDefinition.from_tool(tool)
        for tool in (ticket_tool, knowledge_tool, notification_tool, handoff_tool)
    ))
    graph = CampusSupportTriageGraph(
        planner,
        ticket_specialist,
        KnowledgeSpecialistAgent(knowledge_tool),
        CampusRiskHandoffGuard(),
        NotificationSpecialistAgent(notification_tool),
        handoff_tool,
        checkpointer=checkpointer,
    )
    return CampusSupportTriageRuntime(
        graph=graph,
        planner=planner,
        http_client=http_client,
        trusted_subject_resolver=JavaTrustedSubjectResolver(
            business_service_client
        ),
        memory_service=memory_service,
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
        http_client=httpx.Client(timeout=settings.planner_model_timeout_seconds, trust_env=settings.http_trust_env),
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
        http_client=httpx.Client(timeout=settings.ocr_model_timeout_seconds, trust_env=settings.http_trust_env),
    )
    return PdfOcrFallbackSupportKnowledgeArtifactParser(
        PdfSupportKnowledgeArtifactParser(artifact_root),
        extractor,
    )


def build_dense_index_store(settings: Settings):
    if settings.dense_index_backend == "json":
        return JsonFileDenseSupportKnowledgeIndexStore(_SUPPORT_KNOWLEDGE_DENSE_INDEX_PATH)
    if settings.dense_index_backend == "pgvector":
        if not settings.dense_postgres_dsn:
            raise ValueError("SERVICEFLOW_DENSE_POSTGRES_DSN is required for pgvector")
        from app.infrastructure.pgvector_support_knowledge_index_store import PgvectorSupportKnowledgeIndexStore

        return PgvectorSupportKnowledgeIndexStore(settings.dense_postgres_dsn)
    raise ValueError("unsupported SERVICEFLOW_DENSE_INDEX_BACKEND")


def build_application_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resources = ExitStack()
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
                    httpx.Client(timeout=settings.embedding_model_timeout_seconds, trust_env=settings.http_trust_env),
                ),
                build_dense_index_store(settings),
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
        checkpointer = (
            resources.enter_context(
                open_postgres_checkpointer(settings.memory_postgres_dsn)
            )
            if settings.memory_postgres_dsn is not None
            else None
        )
        memory_service = (
            LongTermMemoryService(
                resources.enter_context(
                    open_postgres_long_term_memory_store(
                        settings.memory_postgres_dsn,
                        application_namespace="serviceflow",
                    )
                ),
                allowed_preference_keys=frozenset({"preferred_response_language"}),
            )
            if settings.memory_postgres_dsn is not None
            else None
        )
        app.state.campus_support_triage_runtime = (
            build_campus_support_triage_runtime(
                settings,
                app.state.support_knowledge_answer_service,
                checkpointer=checkpointer,
                memory_service=memory_service,
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
            resources.close()
            close = getattr(knowledge_service, "close", None)
            if callable(close):
                close()
            ingestion_service.close()

    return lifespan
