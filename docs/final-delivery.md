# ServiceFlow final delivery

## Scope

ServiceFlow is a synthetic campus IT and teaching-service support system. Java
owns authoritative ticket, authorization, transactional Outbox, RabbitMQ, Inbox
idempotency, notifications, and human-handoff persistence. Python owns bounded
Agent coordination, grounded knowledge answers, OCR ingestion, MCP read-only
knowledge access, memory, controlled retrieval expansion, and runtime limits.

```text
Vue → Java login / JWT → Java ticket business service
                 ↓
             transactional Outbox → RabbitMQ → Inbox → notification read model

Vue → Python Triage Coordinator
      ├─ Ticket Specialist → Java authenticated read
      ├─ Knowledge Specialist → citation-backed RAG
      ├─ Notification Specialist → Java authenticated summary
      └─ Risk Guard → human handoff guidance / authenticated handoff task
```

## Demo sequence

1. Sign in with a demonstration account.
2. Create a ticket, open **My tickets**, and show pagination.
3. Sign in as Support/Admin, inspect the queue, claim a ticket, then resolve
   or close it. Explain that Java enforces ownership and optimistic versioning.
4. Use **Agent Triage** for a public knowledge question and inspect citations,
   Coordinator Trace, and execution Harness.
5. Ask an account-compromise or physical-safety question. Show immediate human
   handoff and zero model/tool calls before the safety route.
6. Open **Handoff** to show the durable human task lifecycle.
7. Import a synthetic knowledge artifact and inspect evidence/chunk metadata.

## Local startup

1. Start configured PostgreSQL and RabbitMQ externally.
2. Start `business-service` with its ignored `application-local.yml`.
3. Start `agent-service` with a copied `.env`.
4. Start the Vue client in `frontend/` with `npm run dev`.

## Verification commands

```powershell
# Python focused regression
cd agent-service
$env:PYTHON_DOTENV_DISABLED = "true" # keep tests off developer model settings
..\..\JobScope\.venv\Scripts\python.exe -m pytest tests

# Vue production build
cd ..\frontend
npm run build

# Java unit/process-local tests
cd ..\business-service
.\mvnw.cmd test
```

PostgreSQL, RabbitMQ, OCR, and stdio MCP smoke tests are separate environment
checks. Run only when the required VM/services and credentials are configured;
record the exact commands and results rather than treating skipped Smokes as
passed.

## Recorded VM verification (2026-10-02)

The configured PostgreSQL and RabbitMQ VM was used for opt-in checks. The
following all passed: ServiceFlow Agent short-term checkpoint recovery and
long-term preference isolation (**2 passed**); ticket/Outbox atomic persistence
(**2 passed**); human-handoff, notification, Inbox and status-event persistence
checks; isolated RabbitMQ publisher confirm, real Consumer-to-PostgreSQL Inbox,
transient retry, and dedicated-DLQ checks. The tests create isolated records or
test-only AMQP topology and clean them up.

One deployment action remains external to code: the existing primary RabbitMQ
queue was declared before the current DLX settings and therefore lacks its
dead-letter arguments. RabbitMQ correctly rejects an in-place re-declaration.
Replace that queue only during a planned maintenance window after inspecting or
draining any messages; the application must not delete a shared queue at
startup. The dedicated DLQ Smoke itself passed.

## Claims and boundaries

The project demonstrates a bounded Coordinator plus Specialists, not free-form
autonomous multi-Agent negotiation. It has explicit authorization boundaries,
idempotent Inbox handling, transactional Outbox publishing, controlled retries,
human handoff, grounded citations, and request-scoped model/tool budgets.

It does **not** claim production multi-worker coordination, high availability,
complete disaster recovery, exhaustive OCR/model quality, or load-tested
throughput. All campus data used for demonstration must remain synthetic or
properly authorized.
