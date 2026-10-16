from app.api.report_workspace_api import build_report_router
from app.application.reports.document_workspace import (
    ReportContent, ReportSection, ReportCitation, ReportUnavailableError, ReportConflictError,
)
from app.application.agent.trusted_subject import TrustedSubjectAuthenticationError
from app.infrastructure.clients.business_client import BusinessServiceResponseError
from fastapi import HTTPException


def build_public_knowledge_report_router(settings):
    def runtime(request):
        value=getattr(request.app.state,"campus_support_triage_runtime",None)
        if value is None:
            raise ReportUnavailableError("triage-runtime-unavailable")
        return value

    def owner(request):
        try:
            return runtime(request).resolve_owner_id(request.headers.get("Authorization"))
        except TrustedSubjectAuthenticationError as error:
            raise PermissionError("report-authentication-required") from error
        except BusinessServiceResponseError as error:
            if error.status_code == 401:
                raise PermissionError("report-authentication-required") from error
            if error.status_code == 403:
                raise HTTPException(403, "report-permission-denied") from error
            raise

    def generate(request,owner_id,payload):
        # Only public triage is permitted to supply document contents. JWT is
        # used for ownership above, never forwarded into document generation.
        state=runtime(request).invoke(user_query=payload.query,authorization=None)
        answer=state.get("knowledge_answer")
        if answer is None or answer.status!="answered" or not answer.citations:
            raise ReportConflictError("report-requires-public-knowledge-evidence")
        citations=tuple(ReportCitation(source_reference=c.source_reference,
            evidence_id=c.chunk_id or c.article_id) for c in answer.citations)
        demonstration=any(c.source_reference.startswith("demo://") for c in citations)
        heading="校园知识答复（项目演示资料）" if demonstration else "公共校园知识答复"
        body=("来源提示：以下依据项目演示知识生成，不代表已核验的校园官方指南。\n" if demonstration else "")+answer.answer_text
        return ReportContent(title=payload.title,sections=(
            ReportSection(heading=heading,body=body,citations=citations),))

    return build_report_router(prefix="/api/v1/knowledge/reports",application="serviceflow",
        owner_resolver=owner,generator=generate,settings=settings)
