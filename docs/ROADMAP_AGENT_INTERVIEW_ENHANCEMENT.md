# Agent interview enhancement roadmap

## Identity

ServiceFlow/EduOps remains an **enterprise Agent engineering** project:
bounded Coordinator/Specialists, Java authorization and state ownership,
PostgreSQL, Outbox/Inbox, RabbitMQ, HITL, memory, budgets and Trace. Complex
recruitment document robustness belongs to JobScope and is not duplicated here.

## Ordered work

1. Keep the JobScope complex-document benchmark as the cross-project document
   intelligence workstream; do not alter ServiceFlow's RAG scope for it.
2. Add only ServiceFlow-specific RAG security regression around trusted Java
   identity, tool authorization, Risk Guard and human handoff.
3. Add delivery engineering: CI, Compose, and observability which supplements
   existing Harness/Trace rather than replacing it.
4. Update README/demo material only after the implemented evidence exists.

## Current delivery status

- Java/Python/frontend CI workflow and a no-secret Compose topology are now
  versioned in the repository.
- Compose intentionally keeps model integrations and automatic Outbox delivery
  off. It is a reproducible local topology, not production validation.
- Harness, Coordinator Trace, risk/authorization tests and existing PostgreSQL
  /RabbitMQ opt-in Smokes remain the supported observability and verification
  evidence. No unsupported OpenTelemetry/Langfuse deployment claim is made.

## Boundaries

No open-ended Agent negotiation, self-training, new distributed-worker claims,
Kubernetes, or duplicated large document-RAG stack. Every phase must document
tests, real-Smoke boundaries, regressions and limitations before the next phase.
