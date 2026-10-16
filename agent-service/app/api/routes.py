from __future__ import annotations

import base64
import binascii
import httpx
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from app.application.retrieval.support_knowledge_answering import (
    SupportKnowledgeAnswer,
    SupportKnowledgeAnswerProvider,
)
from app.application.knowledge.support_knowledge_ingestion_service import (
    SupportKnowledgeIngestionService,
    SupportKnowledgeIngestionResult,
)
from app.application.retrieval.support_knowledge_dense_index_preparation import (
    DenseSupportKnowledgeIndexBuildError,
)
from app.application.retrieval.support_knowledge_dense_index_runtime import (
    DenseSupportKnowledgeIndexNotPreparedError,
)
from app.application.retrieval.dense_support_knowledge_chunk_retrieval import (
    DenseSupportKnowledgeIndexUnavailableError,
)
from app.application.knowledge.knowledge_import_access_policy import (
    KnowledgeImportAccessPolicy,
    KnowledgeImportAuthorizationError,
    KnowledgeImportDisabledError,
)
from app.application.knowledge.support_knowledge_article_assembler import (
    SupportKnowledgeArticleAssemblyError,
)
from app.application.knowledge.ocr_page_reading_order import OcrPageSequenceError
from app.application.agent.handoff_guidance import get_handoff_guidance
from app.application.agent.coordinator_trace import CoordinatorTrace
from app.application.agent.agent_harness import (
    AgentHarnessLimitExceededError,
    AgentHarnessSnapshot,
)
from app.application.tools.ticket_lookup_tool import TicketLookupTool
from app.application.workflows.ticket_assistant_graph import TicketAssistantGraph
from app.application.workflows.ticket_lookup_graph import TicketLookupGraph
from app.application.agent.ticket_specialist_agent import (
    TicketAuthorizationRequiredError,
)
from app.application.agent.trusted_subject import TrustedSubjectAuthenticationError
from app.application.memory.long_term_memory import LongTermMemoryEntry
from app.bootstrap import CampusSupportTriageRuntime
from app.config import Settings
from app.domain.ticket_lookup_plan import TicketLookupPlanner
from app.domain.parsed_support_knowledge_document import (
    SupportKnowledgeArtifactParseError,
)
from app.domain.support_knowledge import SupportKnowledgeArticleMetadata
from app.infrastructure.persistence.file_system_support_knowledge_artifact_store import (
    SupportKnowledgeArtifactStoreError,
)
from app.infrastructure.parsers.pdf_ocr_fallback_support_knowledge_artifact_parser import (
    OcrTextExtractionEmptyError,
)
from app.infrastructure.parsers.pdf_page_rendering import PdfPagePixelLimitExceededError
from app.infrastructure.parsers.pdf_support_knowledge_artifact_parser import (
    PdfTextLayerMissingError,
)
from app.infrastructure.parsers.pdfium_pdf_page_renderer import PdfPageRenderError
from app.infrastructure.models.openai_compatible_vision_ocr_text_extractor import (
    OcrTextExtractorUnavailableError,
)
from app.infrastructure.clients.business_client import (
    BusinessServiceClient,
    BusinessServiceHealth,
    BusinessServiceResponseError,
    BusinessServiceUnavailableError,
    BusinessTicket,
    BusinessNotificationSummary,
)
from app.infrastructure.models.qwen_openai_compatible_text_embedder import (
    DenseEmbeddingUnavailableError,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ServiceMetadataResponse(BaseModel):
    stage: str
    business_service_base_url: str
    implemented_capabilities: list[str]
    planned_capabilities: list[str]
    can_execute_external_actions: bool


class BusinessDependencyResponse(BaseModel):
    dependency: str
    health: BusinessServiceHealth


class TicketLookupRequest(BaseModel):
    ticket_id: UUID


class AgentAssistRequest(BaseModel):
    user_query: str

    @field_validator("user_query")
    @classmethod
    def user_query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_query must not be blank")
        return value.strip()


class SupportKnowledgeAnswerRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=5)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()


class PreferenceWriteRequest(BaseModel):
    preference_key: Literal["preferred_response_language"]
    preference_value: Literal["zh-CN", "en-US"]
    user_consented: Literal[True]


class PreferenceResponse(BaseModel):
    preference_key: str
    preference_value: str
    consented_at: str
    created_at: str
    updated_at: str
    revision: int


class PreferencesResponse(BaseModel):
    preferences: list[PreferenceResponse]


class ForgetAllPreferencesResponse(BaseModel):
    deleted_count: int


class ConversationTurnResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationResponse(BaseModel):
    turns: list[ConversationTurnResponse]


class SupportKnowledgeCitationResponse(BaseModel):
    article_id: str
    title: str
    source_reference: str
    chunk_id: str | None = None
    fragment_location: str | None = None


class SupportKnowledgeRetrievalTraceStepResponse(BaseModel):
    stage: str
    status: Literal["completed", "applied", "degraded", "refused"]


class SupportKnowledgeAnswerResponse(BaseModel):
    status: str
    answer_text: str
    citations: list[SupportKnowledgeCitationResponse]
    model_called: bool
    model_identity: str | None
    retrieval_strategy: Literal[
        "lexical", "hybrid", "hybrid_reranked", "hybrid_rerank_degraded"
    ] = "lexical"
    reranker_status: Literal["not_configured", "applied", "degraded"] = "not_configured"
    reranker_identity: str | None = None
    reranker_failure_code: str | None = None
    initial_evidence_count: int | None = None
    secondary_search_attempted: bool = False
    secondary_search_reason: str | None = None
    query_rewrite_attempted: bool = False
    query_rewrite_status: Literal["not_requested", "applied", "degraded"] = "not_requested"
    query_rewriter_identity: str | None = None
    query_rewrite_failure_code: str | None = None
    retrieval_trace: list[SupportKnowledgeRetrievalTraceStepResponse] = Field(
        default_factory=list
    )


class SupportKnowledgeImportMetadataRequest(BaseModel):
    article_id: str = Field(min_length=1, max_length=120)
    category: Literal[
        "account",
        "campus_network",
        "teaching_system",
        "classroom_equipment",
        "service_process",
    ]
    fallback_title: str = Field(min_length=1, max_length=200)
    source_review_status: Literal["reviewed", "demonstration"]
    source_review_reference: str = Field(min_length=1, max_length=500)
    corpus_version: str = Field(min_length=1, max_length=80)


class SupportKnowledgeImportRequest(BaseModel):
    source_reference: str = Field(min_length=1, max_length=1000)
    source_kind: Literal["official_campus", "demonstration"]
    original_filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)
    metadata: SupportKnowledgeImportMetadataRequest

    @field_validator("content_base64")
    @classmethod
    def content_must_be_valid_base64(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("content_base64 must be valid base64") from error
        if not decoded:
            raise ValueError("content_base64 must decode to non-blank content")
        return value

    def decoded_content(self) -> bytes:
        return base64.b64decode(self.content_base64, validate=True)

    def to_article_metadata(self) -> SupportKnowledgeArticleMetadata:
        return SupportKnowledgeArticleMetadata(
            article_id=self.metadata.article_id,
            category=self.metadata.category,
            fallback_title=self.metadata.fallback_title,
            source_reference=self.source_reference,
            source_kind=self.source_kind,
            source_review_status=self.metadata.source_review_status,
            source_review_reference=self.metadata.source_review_reference,
            corpus_version=self.metadata.corpus_version,
        )


class SupportKnowledgeImportResponse(BaseModel):
    artifact_id: str
    document_format: str
    artifact_content_sha256: str
    parsed_title: str | None
    parsed_text_length: int
    article_id: str
    article_title: str
    source_content_sha256: str
    corpus_changed: bool
    corpus_revision: int
    source_reference: str
    source_kind: Literal["official_campus", "demonstration"]
    source_review_status: Literal["reviewed", "demonstration"]
    source_review_reference: str
    dense_index_status: Literal["disabled", "ready", "stale"]
    dense_index_failure_code: str | None


class CampusSupportTriageResponse(BaseModel):
    decision: Literal[
        "lookup_ticket",
        "get_notification_summary",
        "answer_support_knowledge",
        "handoff_to_human",
        "refuse",
    ]
    reason: str
    handoff_reason: str | None
    handoff_guidance: "HandoffGuidanceResponse | None"
    ticket: BusinessTicket | None
    knowledge_answer: SupportKnowledgeAnswerResponse | None
    notification_summary: BusinessNotificationSummary | None = None
    trace: "CoordinatorTraceResponse"
    harness: "AgentHarnessResponse"

    @model_validator(mode="after")
    def validate_decision_payload(self) -> "CampusSupportTriageResponse":
        if self.decision == "lookup_ticket":
            if self.ticket is None:
                raise ValueError("lookup_ticket response requires ticket")
            if any(
                value is not None
                for value in (
                    self.handoff_reason,
                    self.handoff_guidance,
                    self.knowledge_answer,
                    self.notification_summary,
                )
            ):
                raise ValueError("lookup_ticket response must contain only ticket payload")
        elif self.decision == "get_notification_summary":
            if self.notification_summary is None:
                raise ValueError(
                    "get_notification_summary response requires notification_summary"
                )
            if any(
                value is not None
                for value in (
                    self.handoff_reason,
                    self.handoff_guidance,
                    self.ticket,
                    self.knowledge_answer,
                )
            ):
                raise ValueError(
                    "get_notification_summary response must contain only notification_summary"
                )
        elif self.decision == "answer_support_knowledge":
            if self.knowledge_answer is None:
                raise ValueError("answer_support_knowledge response requires knowledge_answer")
            if any(
                value is not None
                for value in (
                    self.handoff_reason,
                    self.handoff_guidance,
                    self.ticket,
                    self.notification_summary,
                )
            ):
                raise ValueError(
                    "answer_support_knowledge response must contain only knowledge payload"
                )
        elif self.decision == "handoff_to_human":
            if self.handoff_reason is None or self.handoff_guidance is None:
                raise ValueError(
                    "handoff_to_human response requires handoff_reason and handoff_guidance"
                )
            if (
                self.ticket is not None
                or self.knowledge_answer is not None
                or self.notification_summary is not None
            ):
                raise ValueError("handoff_to_human response must not contain tool payload")
        elif any(
            value is not None
            for value in (
                self.handoff_reason,
                self.handoff_guidance,
                self.ticket,
                self.knowledge_answer,
                self.notification_summary,
            )
        ):
            raise ValueError("refuse response must not contain an execution payload")
        return self


class HandoffGuidanceResponse(BaseModel):
    reason: str
    title: str
    message: str
    immediate_actions: list[str]


class CoordinatorTraceStepResponse(BaseModel):
    node: str
    specialist_identity: str | None
    tool_name: str | None
    elapsed_seconds: float
    status: str
    decision: str | None
    failure_code: str | None


class CoordinatorTraceResponse(BaseModel):
    request_id: str
    steps: list[CoordinatorTraceStepResponse]


class AgentHarnessStepResponse(BaseModel):
    operation_kind: Literal["model", "tool"]
    operation_name: str
    status: Literal["succeeded", "failed", "rejected"]
    elapsed_seconds: float
    failure_code: str | None


class AgentHarnessResponse(BaseModel):
    model_call_count: int
    tool_call_count: int
    elapsed_seconds: float
    steps: list[AgentHarnessStepResponse]


def _to_support_knowledge_answer_response(
    result: SupportKnowledgeAnswer,
) -> SupportKnowledgeAnswerResponse:
    return SupportKnowledgeAnswerResponse(
        status=result.status,
        answer_text=result.answer_text,
        citations=[
            SupportKnowledgeCitationResponse(
                article_id=citation.article_id,
                title=citation.title,
                source_reference=citation.source_reference,
                chunk_id=citation.chunk_id,
                fragment_location=citation.fragment_location,
            )
            for citation in result.citations
        ],
        model_called=result.model_called,
        model_identity=result.model_identity,
        retrieval_strategy=result.retrieval_strategy,
        reranker_status=result.reranker_status,
        reranker_identity=result.reranker_identity,
        reranker_failure_code=result.reranker_failure_code,
        initial_evidence_count=result.initial_evidence_count,
        secondary_search_attempted=result.secondary_search_attempted,
        secondary_search_reason=result.secondary_search_reason,
        query_rewrite_attempted=result.query_rewrite_attempted,
        query_rewrite_status=result.query_rewrite_status,
        query_rewriter_identity=result.query_rewriter_identity,
        query_rewrite_failure_code=result.query_rewrite_failure_code,
        retrieval_trace=[
            SupportKnowledgeRetrievalTraceStepResponse(
                stage=step.stage,
                status=step.status,
            )
            for step in result.retrieval_trace
        ],
    )


def _to_coordinator_trace_response(
    trace: CoordinatorTrace,
) -> CoordinatorTraceResponse:
    return CoordinatorTraceResponse(
        request_id=trace.request_id,
        steps=[
            CoordinatorTraceStepResponse(
                node=step.node,
                specialist_identity=step.specialist_identity,
                tool_name=step.tool_name,
                elapsed_seconds=step.elapsed_seconds,
                status=step.status,
                decision=step.decision,
                failure_code=step.failure_code,
            )
            for step in trace.steps
        ],
    )


def _to_agent_harness_response(
    snapshot: AgentHarnessSnapshot,
) -> AgentHarnessResponse:
    """Expose only operational metadata; never prompts, credentials, or payloads."""

    return AgentHarnessResponse(
        model_call_count=snapshot.model_call_count,
        tool_call_count=snapshot.tool_call_count,
        elapsed_seconds=snapshot.elapsed_seconds,
        steps=[
            AgentHarnessStepResponse(
                operation_kind=step.operation_kind,
                operation_name=step.operation_name,
                status=step.status,
                elapsed_seconds=step.elapsed_seconds,
                failure_code=step.failure_code,
            )
            for step in snapshot.steps
        ],
    )


def _to_support_knowledge_import_response(
    result: SupportKnowledgeIngestionResult,
    *,
    dense_index_status: Literal["disabled", "ready", "stale"],
    dense_index_failure_code: str | None,
) -> SupportKnowledgeImportResponse:
    return SupportKnowledgeImportResponse(
        artifact_id=result.artifact.artifact_id,
        document_format=result.artifact.document_format,
        artifact_content_sha256=result.artifact.content_sha256,
        parsed_title=result.parsed_document.title,
        parsed_text_length=len(result.parsed_document.text),
        article_id=result.article.article_id,
        article_title=result.article.title,
        source_content_sha256=result.article.source_content_sha256,
        corpus_changed=result.corpus_changed,
        corpus_revision=result.corpus_revision,
        source_reference=result.article.source_reference,
        source_kind=result.article.source_kind,
        source_review_status=result.article.source_review_status,
        source_review_reference=result.article.source_review_reference,
        dense_index_status=dense_index_status,
        dense_index_failure_code=dense_index_failure_code,
    )


def create_router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="UP",
            service=settings.service_name,
            version=settings.version,
            environment=settings.environment,
        )

    @router.get(
        "/api/v1/meta",
        response_model=ServiceMetadataResponse,
        tags=["system"],
    )
    def metadata() -> ServiceMetadataResponse:
        return ServiceMetadataResponse(
            stage="bounded-multi-specialist-workflow",
            business_service_base_url=settings.business_service_base_url,
            implemented_capabilities=[
                "typed-health-contract",
                "explicit-java-service-boundary",
                "java-ticket-lookup-tool",
                "langgraph-planning-and-routing",
                "campus-support-triage-coordinator",
                "ticket-specialist",
                "knowledge-specialist",
                "notification-specialist",
                "ticket-to-knowledge-sequential-collaboration",
                "risk-handoff-guidance",
                "campus-support-knowledge-retrieval",
                "extractive-grounded-knowledge-answering",
            ],
            planned_capabilities=[
                "llm-grounded-knowledge-synthesis",
                "persistent-checkpoint",
                "persistent-human-handoff-task",
                "runtime-trace",
                "multi-agent-golden-evaluation",
            ],
            can_execute_external_actions=False,
        )

    @router.get(
        "/api/v1/dependencies/business/health",
        response_model=BusinessDependencyResponse,
        tags=["system"],
    )
    def business_dependency_health() -> BusinessDependencyResponse:
        try:
            with httpx.Client(
                timeout=settings.business_service_timeout_seconds
            ) as http_client:
                health_result = BusinessServiceClient(
                    settings.business_service_base_url,
                    http_client,
                ).get_health()
        except BusinessServiceUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail="business service is unavailable",
            ) from error
        except AgentHarnessLimitExceededError as error:
            raise HTTPException(
                status_code=503,
                detail=error.failure_code,
            ) from error
        return BusinessDependencyResponse(
            dependency="business-service",
            health=health_result,
        )

    @router.post(
        "/api/v1/knowledge/answer",
        response_model=SupportKnowledgeAnswerResponse,
        tags=["knowledge"],
    )
    def answer_support_knowledge(
        request: SupportKnowledgeAnswerRequest,
        http_request: Request,
    ) -> SupportKnowledgeAnswerResponse:
        service: SupportKnowledgeAnswerProvider = (
            http_request.app.state.support_knowledge_answer_service
        )
        try:
            result = service.answer(request.question, top_k=request.top_k)
        except (
            DenseEmbeddingUnavailableError,
            DenseSupportKnowledgeIndexUnavailableError,
            DenseSupportKnowledgeIndexNotPreparedError,
        ) as error:
            # A configured Hybrid request cannot honestly pretend its Dense side ran.
            # Keep provider details out of the external response.
            raise HTTPException(
                status_code=503,
                detail="support knowledge retrieval is temporarily unavailable",
            ) from error
        return _to_support_knowledge_answer_response(result)

    @router.get(
        "/api/v1/memory/preferences",
        response_model=PreferencesResponse,
        tags=["memory"],
    )
    def list_preferences(
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> PreferencesResponse:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            entries = runtime.list_authenticated_preferences(
                authorization=authorization
            )
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(401, "a valid Bearer token is required") from error
        return PreferencesResponse(
            preferences=[_to_preference_response(entry) for entry in entries]
        )

    @router.put(
        "/api/v1/memory/preferences",
        response_model=PreferenceResponse,
        tags=["memory"],
    )
    def remember_preference(
        payload: PreferenceWriteRequest,
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> PreferenceResponse:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            entry = runtime.remember_preference(
                authorization=authorization,
                preference_key=payload.preference_key,
                preference_value=payload.preference_value,
                user_consented=payload.user_consented,
            )
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(401, "a valid Bearer token is required") from error
        except RuntimeError as error:
            raise HTTPException(503, "long-term memory is unavailable") from error
        return _to_preference_response(entry)

    @router.delete(
        "/api/v1/memory/preferences/{preference_key}",
        status_code=204,
        tags=["memory"],
    )
    def forget_preference(
        preference_key: Literal["preferred_response_language"],
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            runtime.forget_preference(
                authorization=authorization,
                preference_key=preference_key,
            )
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(401, "a valid Bearer token is required") from error
        except RuntimeError as error:
            raise HTTPException(503, "long-term memory is unavailable") from error

    @router.delete(
        "/api/v1/memory/preferences",
        response_model=ForgetAllPreferencesResponse,
        tags=["memory"],
    )
    def forget_all_preferences(
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> ForgetAllPreferencesResponse:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            deleted_count = runtime.forget_all_preferences(
                authorization=authorization
            )
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(401, "a valid Bearer token is required") from error
        except RuntimeError as error:
            raise HTTPException(503, "long-term memory is unavailable") from error
        return ForgetAllPreferencesResponse(deleted_count=deleted_count)

    @router.get(
        "/api/v1/memory/conversation",
        response_model=ConversationResponse,
        tags=["memory"],
    )
    def get_conversation(
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> ConversationResponse:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            turns = runtime.get_authenticated_conversation_turns(
                authorization=authorization
            )
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(401, "a valid Bearer token is required") from error
        except RuntimeError as error:
            raise HTTPException(503, "triage conversation memory is unavailable") from error
        return ConversationResponse(
            turns=[ConversationTurnResponse(**turn) for turn in turns]
        )

    @router.delete(
        "/api/v1/memory/conversation",
        status_code=204,
        tags=["memory"],
    )
    def clear_conversation(
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            runtime.clear_authenticated_conversation(authorization=authorization)
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(401, "a valid Bearer token is required") from error
        except RuntimeError as error:
            raise HTTPException(503, "triage conversation memory is unavailable") from error

    @router.post(
        "/api/v1/knowledge/imports",
        response_model=SupportKnowledgeImportResponse,
        status_code=201,
        tags=["knowledge-admin"],
    )
    def import_support_knowledge(
        payload: SupportKnowledgeImportRequest,
        http_request: Request,
        x_knowledge_import_token: Annotated[str | None, Header()] = None,
    ) -> SupportKnowledgeImportResponse:
        access_policy: KnowledgeImportAccessPolicy = (
            http_request.app.state.knowledge_import_access_policy
        )
        try:
            access_policy.require_authorized(x_knowledge_import_token)
        except KnowledgeImportDisabledError as error:
            # A disabled write endpoint is intentionally not discoverable as usable.
            raise HTTPException(status_code=404, detail="knowledge import is unavailable") from error
        except KnowledgeImportAuthorizationError as error:
            raise HTTPException(status_code=403, detail="knowledge import access denied") from error
        service: SupportKnowledgeIngestionService = (
            http_request.app.state.support_knowledge_ingestion_service
        )
        try:
            result = service.ingest(
                source_reference=payload.source_reference,
                source_kind=payload.source_kind,
                original_filename=payload.original_filename,
                content=payload.decoded_content(),
                metadata=payload.to_article_metadata(),
            )
        except (
            SupportKnowledgeArtifactStoreError,
            SupportKnowledgeArtifactParseError,
            SupportKnowledgeArticleAssemblyError,
            OcrPageSequenceError,
            PdfPagePixelLimitExceededError,
            PdfPageRenderError,
            OcrTextExtractorUnavailableError,
        ) as error:
            raise _to_support_knowledge_import_http_exception(error) from error
        dense_index_status: Literal["disabled", "ready", "stale"] = "disabled"
        dense_index_failure_code: str | None = None
        dense_runtime = getattr(
            http_request.app.state,
            "support_knowledge_dense_index_runtime",
            None,
        )
        if dense_runtime is not None:
            try:
                dense_runtime.refresh()
                dense_index_status = "ready"
            except DenseEmbeddingUnavailableError as error:
                # The file import has already committed.  Preserve that fact and expose
                # only a stable, non-secret failure code for the pending dense refresh.
                dense_index_status = "stale"
                dense_index_failure_code = error.failure_code
            except DenseSupportKnowledgeIndexBuildError:
                dense_index_status = "stale"
                dense_index_failure_code = "dense-index-build-invalid"
        return _to_support_knowledge_import_response(
            result,
            dense_index_status=dense_index_status,
            dense_index_failure_code=dense_index_failure_code,
        )


    @router.post(
        "/api/v1/agent/triage",
        response_model=CampusSupportTriageResponse,
        tags=["agent"],
    )
    def triage_campus_support(
        request: AgentAssistRequest,
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> CampusSupportTriageResponse:
        runtime: CampusSupportTriageRuntime = (
            http_request.app.state.campus_support_triage_runtime
        )
        try:
            result = runtime.invoke(
                user_query=request.user_query,
                authorization=authorization,
            )
        except TrustedSubjectAuthenticationError as error:
            raise HTTPException(
                status_code=401,
                detail="a valid Bearer token is required",
            ) from error
        except TicketAuthorizationRequiredError as error:
            raise HTTPException(status_code=401, detail="Bearer token is required") from error
        except BusinessServiceResponseError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail="business ticket request was rejected",
            ) from error
        except BusinessServiceUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail="business service is unavailable",
            ) from error
        knowledge_answer = result["knowledge_answer"]
        handoff_reason = result["handoff_reason"]
        handoff_guidance = (
            get_handoff_guidance(handoff_reason)
            if handoff_reason is not None
            else None
        )
        return CampusSupportTriageResponse(
            decision=result["decision"],
            reason=result["reason"],
            handoff_reason=handoff_reason,
            handoff_guidance=(
                HandoffGuidanceResponse(
                    reason=handoff_guidance.reason,
                    title=handoff_guidance.title,
                    message=handoff_guidance.message,
                    immediate_actions=list(handoff_guidance.immediate_actions),
                )
                if handoff_guidance is not None
                else None
            ),
            ticket=result["ticket"],
            knowledge_answer=(
                _to_support_knowledge_answer_response(knowledge_answer)
                if knowledge_answer is not None
                else None
            ),
            notification_summary=result["notification_summary"],
            trace=_to_coordinator_trace_response(result["trace"]),
            harness=_to_agent_harness_response(result["harness_snapshot"]),
        )

    @router.post("/api/v1/tools/tickets/lookup", tags=["tools"])
    def lookup_ticket(
        request: TicketLookupRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> BusinessTicket:
        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token is required")
        try:
            with httpx.Client(
                timeout=settings.business_service_timeout_seconds
            ) as http_client:
                client = BusinessServiceClient(
                    settings.business_service_base_url,
                    http_client,
                )
                return TicketLookupGraph(TicketLookupTool(client)).invoke(
                    ticket_id=request.ticket_id,
                    authorization=authorization,
                )
        except BusinessServiceResponseError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail="business ticket request was rejected",
            ) from error
        except BusinessServiceUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail="business service is unavailable",
            ) from error

    @router.post("/api/v1/agent/assist", tags=["agent"])
    def assist_with_ticket_lookup(
        request: AgentAssistRequest,
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token is required")
        try:
            with httpx.Client(
                timeout=settings.business_service_timeout_seconds
            ) as http_client:
                client = BusinessServiceClient(
                    settings.business_service_base_url,
                    http_client,
                )
                active_planner: TicketLookupPlanner = (
                    http_request.app.state.ticket_lookup_planner
                )
                return TicketAssistantGraph(
                    active_planner,
                    TicketLookupTool(client),
                ).invoke(
                    user_query=request.user_query,
                    authorization=authorization,
                )
        except BusinessServiceResponseError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail="business ticket request was rejected",
            ) from error
        except BusinessServiceUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail="business service is unavailable",
            ) from error

    return router

def _to_preference_response(entry: LongTermMemoryEntry) -> PreferenceResponse:
    return PreferenceResponse(
        preference_key=entry.preference_key,
        preference_value=entry.preference_value,
        consented_at=entry.consented_at.isoformat(),
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
        revision=entry.revision,
    )


def _to_support_knowledge_import_http_exception(error: Exception) -> HTTPException:
    """Expose stable import failure codes without returning provider internals."""
    if isinstance(error, OcrTextExtractorUnavailableError):
        return HTTPException(
            status_code=503,
            detail={
                "code": error.failure_code,
                "message": "OCR model is currently unavailable",
            },
        )
    if isinstance(error, PdfPagePixelLimitExceededError):
        return HTTPException(
            status_code=422,
            detail={
                "code": "pdf-page-pixel-limit-exceeded",
                "message": "PDF page is too large to render safely",
            },
        )
    if isinstance(error, PdfTextLayerMissingError):
        return HTTPException(
            status_code=422,
            detail={
                "code": "pdf-text-layer-missing",
                "message": "PDF has no extractable text layer",
            },
        )
    if isinstance(error, OcrTextExtractionEmptyError):
        return HTTPException(
            status_code=422,
            detail={
                "code": "ocr-no-text-extracted",
                "message": "OCR produced no usable text",
            },
        )
    if isinstance(error, OcrPageSequenceError):
        return HTTPException(
            status_code=422,
            detail={
                "code": "ocr-page-sequence-invalid",
                "message": "OCR page sequence cannot be trusted",
            },
        )
    if isinstance(error, PdfPageRenderError):
        return HTTPException(
            status_code=422,
            detail={
                "code": "pdf-page-render-failed",
                "message": "PDF could not be rendered for OCR",
            },
        )
    return HTTPException(
        status_code=422,
        detail={
            "code": "support-knowledge-import-not-accepted",
            "message": "support knowledge import could not be accepted",
        },
    )
