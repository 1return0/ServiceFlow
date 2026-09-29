<script setup lang="ts">
import { ref } from "vue";
import type { KnowledgeImportResponse } from "@/api/contracts";
import { agentApi } from "@/api/agent";

const file = ref<File | null>(null);
const importToken = ref("");
const articleId = ref("");
const fallbackTitle = ref("");
const sourceReference = ref("");
const result = ref<KnowledgeImportResponse | null>(null);
const error = ref<string | null>(null);

function selectFile(event: Event) { file.value = (event.target as HTMLInputElement).files?.[0] ?? null; }
function asBase64(content: ArrayBuffer) { return btoa(Array.from(new Uint8Array(content), byte => String.fromCharCode(byte)).join("")); }

async function importFile() {
  if (!file.value) { error.value = "请选择要导入的文件"; return; }
  error.value = null; result.value = null;
  try {
    const contentBase64 = asBase64(await file.value.arrayBuffer());
    result.value = await agentApi.importKnowledge({
      source_reference: sourceReference.value,
      source_kind: "demonstration",
      original_filename: file.value.name,
      content_base64: contentBase64,
      metadata: {
        article_id: articleId.value,
        category: "service_process",
        fallback_title: fallbackTitle.value,
        source_review_status: "demonstration",
        source_review_reference: "frontend demonstration import",
        corpus_version: "frontend-import-v1",
      },
    }, importToken.value);
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "知识导入失败"; }
}
</script>

<template>
  <section><p class="eyebrow">Knowledge Admin</p><h1>知识材料导入</h1>
    <p class="muted">此入口仅转发一次性导入令牌；令牌不会写入浏览器存储。</p>
    <form class="form-card" @submit.prevent="importFile">
      <label>导入令牌<input v-model="importToken" type="password" required /></label>
      <label>来源说明<input v-model.trim="sourceReference" required placeholder="公开来源或审核记录" /></label>
      <label>Article ID<input v-model.trim="articleId" required /></label>
      <label>备用标题<input v-model.trim="fallbackTitle" required /></label>
      <label>文件<input type="file" accept=".html,.htm,.pdf,.docx" required @change="selectFile" /></label>
      <button type="submit">导入并解析</button>
    </form>
    <p v-if="error" class="error-message">{{ error }}</p>
    <article v-if="result" class="result-card"><h2>{{ result.article_title }}</h2><p>Corpus revision: {{ result.corpus_revision }} · changed: {{ result.corpus_changed }}</p><code>{{ result.source_content_sha256 }}</code></article>
  </section>
</template>
