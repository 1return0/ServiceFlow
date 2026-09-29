<script setup lang="ts">
import { ref } from "vue";
import type { HandoffTask } from "@/api/contracts";
import { businessApi } from "@/api/business";

const tasks = ref<HandoffTask[]>([]);
const error = ref<string | null>(null);

async function load() { try { error.value = null; tasks.value = await businessApi.listOpenHandoffs(); } catch (cause) { error.value = cause instanceof Error ? cause.message : "人工任务加载失败"; } }
async function claim(id: string) { await businessApi.claimHandoff(id); await load(); }
async function resolve(id: string) { await businessApi.resolveHandoff(id); await load(); }
</script>

<template>
  <section><p class="eyebrow">Human Handoff</p><h1>人工交接任务</h1>
    <p class="muted">仅 Support Agent 或 Admin 可访问。页面不代表系统自动处理高风险事项。</p>
    <button type="button" @click="load">加载待处理任务</button><p v-if="error" class="error-message">{{ error }}</p>
    <article v-for="task in tasks" :key="task.id" class="result-card"><h2>{{ task.status }} · {{ task.handoffReason }}</h2><p>request_id: {{ task.requestId }}</p><p>负责人：{{ task.assignedTo ?? "未领取" }}</p>
      <button v-if="task.status === 'PENDING'" type="button" @click="claim(task.id)">领取</button>
      <button v-if="task.status === 'CLAIMED'" type="button" @click="resolve(task.id)">解决</button>
    </article>
  </section>
</template>
