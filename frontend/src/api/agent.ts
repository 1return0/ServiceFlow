import type { KnowledgeAnswer, KnowledgeImportResponse, TriageResponse } from "./contracts";
import { agentApiClient } from "./clients";

export const agentApi = {
  answerKnowledge(question: string) {
    return agentApiClient.post<KnowledgeAnswer>("/api/v1/knowledge/answer", { question, top_k: 3 });
  },
  triage(userQuery: string) {
    return agentApiClient.post<TriageResponse>("/api/v1/agent/triage", { user_query: userQuery });
  },
  importKnowledge(payload: unknown, importToken: string) {
    return agentApiClient.post<KnowledgeImportResponse>("/api/v1/knowledge/imports", payload, {
      "X-Knowledge-Import-Token": importToken,
    });
  },
};
