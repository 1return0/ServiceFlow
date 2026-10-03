# ServiceFlow delivery-engineering course cursor

This is a follow-up cursor. The core Java/Agent lessons remain in the existing
course material; these lessons explain the new delivery boundary without
duplicating JobScope's document-RAG module.

| Cursor | Lesson | Code and evidence |
| --- | --- | --- |
| D1 | Why ServiceFlow is bounded Specialist coordination, not open-ended autonomous multi-agent | `agent-service/app/application/workflows/campus_support_triage_graph.py`, `README.md` |
| D2 | Java owns JWT/RBAC and ticket writes; Agent owns safe orchestration | `business-service/.../SecurityConfig.java`, `agent-service/app/infrastructure/business_client.py` |
| D3 | Outbox/Inbox/RabbitMQ and why Compose keeps scheduler disabled | `business-service/src/main/resources/application.yml`, `compose.yaml` |
| D4 | Harness and redacted Trace as local observability; what they do not prove | `agent-service/app/application/agent_harness.py`, `coordinator_trace.py` |
| D5 | CI: independent Java, Python and Vue build gates | `.github/workflows/ci.yml` |
| D6 | Compose topology and secrets/model toggles | `compose.yaml`, `.env.example`, `frontend/nginx.conf` |
| D7 | How to state verification boundaries in an interview | `README.md`, `docs/final-delivery.md` |

The document-layout benchmark is learned from the JobScope cursor because the
feature is intentionally not duplicated in ServiceFlow.
