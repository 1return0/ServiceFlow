<script setup lang="ts">
import { ref } from "vue";

import type { TriageResponse } from "@/api/contracts";
import { agentApi } from "@/api/agent";
import TracePanel from "@/components/TracePanel.vue";

const userQuery = ref("");
const result = ref<TriageResponse | null>(null);
const error = ref<string | null>(null);
const submitting = ref(false);

async function triage() {
  error.value = null;
  result.value = null;
  submitting.value = true;
  try { result.value = await agentApi.triage(userQuery.value); }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "协同请求失败"; }
  finally { submitting.value = false; }
}
</script>

<template>
  <section><p class="eyebrow">Multi Specialist Coordinator</p><h1>校园服务协同助手</h1>
    <form class="form-card" @submit.prevent="triage">
      <label>问题<textarea v-model.trim="userQuery" required placeholder="例如：查询工单 00000000-0000-0000-0000-000000000000" /></label>
      <button :disabled="submitting" type="submit">{{ submitting ? "正在处理" : "开始协同" }}</button>
    </form>
    <p v-if="error" class="error-message">{{ error }}</p>
    <template v-if="result">
      <article class="result-card"><p class="eyebrow">{{ result.decision }}</p><h2>{{ result.reason }}</h2>
        <template v-if="result.ticket"><p>{{ result.ticket.summary }}</p><code>{{ result.ticket.id }}</code></template>
        <template v-if="result.notification_summary"><p>未读通知：{{ result.notification_summary.unreadCount }}</p></template>
        <template v-if="result.knowledge_answer"><p>{{ result.knowledge_answer.answer_text }}</p>
          <ul><li v-for="citation in result.knowledge_answer.citations" :key="citation.chunk_id ?? citation.article_id">{{ citation.title }} · {{ citation.fragment_location ?? citation.source_reference }}</li></ul>
        </template>
        <template v-if="result.handoff_guidance"><h3>{{ result.handoff_guidance.title }}</h3><p>{{ result.handoff_guidance.message }}</p>
          <ul><li v-for="action in result.handoff_guidance.immediate_actions" :key="action">{{ action }}</li></ul>
        </template>
      </article>
      <TracePanel :trace="result.trace" />
    </template>
  </section>
</template>
