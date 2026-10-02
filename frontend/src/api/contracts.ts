export interface ResultEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

export interface LoginResponse {
  accessToken: string;
  tokenType: "Bearer";
  expiresAt: string;
}

export interface Ticket {
  id: string;
  requesterReference: string;
  category: string;
  summary: string;
  submittedAt: string;
  status: string;
  assigneeReference: string | null;
  claimedAt: string | null;
  version: number;
}

export interface PageResponse<T> {
  page: number;
  size: number;
  total: number;
  items: T[];
}

export interface Notification {
  id: string;
  ticketId: string;
  notificationType: string;
  message: string;
  createdAt: string;
  readAt: string | null;
}

export interface NotificationSummary {
  unreadCount: number;
}

export interface HandoffTask {
  id: string;
  requestId: string;
  requesterReference: string;
  handoffReason: string;
  status: "PENDING" | "CLAIMED" | "RESOLVED";
  assignedTo: string | null;
  createdAt: string;
  claimedAt: string | null;
  resolvedAt: string | null;
  version: number;
}

export interface KnowledgeCitation {
  article_id: string;
  title: string;
  source_reference: string;
  chunk_id: string | null;
  fragment_location: string | null;
}

export interface KnowledgeAnswer {
  status: string;
  answer_text: string;
  citations: KnowledgeCitation[];
  model_called: boolean;
  model_identity: string | null;
}

export interface CoordinatorTraceStep {
  node: string;
  specialist_identity: string | null;
  tool_name: string | null;
  elapsed_seconds: number;
  status: string;
  decision: string | null;
  failure_code: string | null;
}

export interface CoordinatorTrace {
  request_id: string;
  steps: CoordinatorTraceStep[];
}

export interface AgentHarnessStep {
  operation_kind: "model" | "tool";
  operation_name: string;
  status: "succeeded" | "failed" | "rejected";
  elapsed_seconds: number;
  failure_code: string | null;
}

export interface AgentHarness {
  model_call_count: number;
  tool_call_count: number;
  elapsed_seconds: number;
  steps: AgentHarnessStep[];
}

export interface HandoffGuidance {
  reason: string;
  title: string;
  message: string;
  immediate_actions: string[];
}

export interface TriageResponse {
  decision: "lookup_ticket" | "get_notification_summary" | "answer_support_knowledge" | "handoff_to_human" | "refuse";
  reason: string;
  handoff_reason: string | null;
  handoff_guidance: HandoffGuidance | null;
  ticket: Ticket | null;
  knowledge_answer: KnowledgeAnswer | null;
  notification_summary: NotificationSummary | null;
  trace: CoordinatorTrace;
  harness: AgentHarness;
}

export interface KnowledgeImportResponse {
  artifact_id: string;
  document_format: string;
  artifact_content_sha256: string;
  parsed_title: string | null;
  parsed_text_length: number;
  article_id: string;
  article_title: string;
  source_content_sha256: string;
  corpus_changed: boolean;
  corpus_revision: number;
  source_reference: string;
  source_kind: "official_campus" | "demonstration";
  source_review_status: "reviewed" | "demonstration";
  source_review_reference: string;
}
