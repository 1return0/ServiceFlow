<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { Notification, NotificationSummary } from "@/api/contracts";
import { businessApi } from "@/api/business";

const notifications = ref<Notification[]>([]);
const summary = ref<NotificationSummary | null>(null);
const error = ref<string | null>(null);

async function load() {
  error.value = null;
  try {
    [notifications.value, summary.value] = await Promise.all([businessApi.listNotifications(), businessApi.notificationSummary()]);
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "通知加载失败"; }
}
async function markRead(id: string) { await businessApi.markNotificationRead(id); await load(); }
onMounted(() => { void load(); });
</script>

<template>
  <section><p class="eyebrow">Notifications</p><h1>通知 <small v-if="summary">未读 {{ summary.unreadCount }}</small></h1>
    <p v-if="error" class="error-message">{{ error }}</p>
    <button type="button" @click="load">刷新</button>
    <article v-for="item in notifications" :key="item.id" class="result-card">
      <strong>{{ item.notificationType }}</strong><p>{{ item.message }}</p><small>{{ item.createdAt }}</small>
      <button v-if="!item.readAt" type="button" @click="markRead(item.id)">标为已读</button>
    </article>
  </section>
</template>
