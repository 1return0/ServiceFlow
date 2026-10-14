<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiRequestError } from "@/api/http";
import type { Ticket } from "@/api/contracts";
import { businessApi } from "@/api/business";

type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
type TicketViewMode = "mine" | "queue";

const categories = [
  { value: "CAMPUS_NETWORK", label: "校园网络" },
  { value: "TEACHING_SYSTEM", label: "教学系统" },
  { value: "CLASSROOM_EQUIPMENT", label: "教室设备" },
  { value: "ACCOUNT", label: "账号服务" },
];

const allowedTransitions: Record<TicketStatus, TicketStatus[]> = {
  OPEN: ["IN_PROGRESS"],
  IN_PROGRESS: ["RESOLVED"],
  RESOLVED: ["CLOSED", "IN_PROGRESS"],
  CLOSED: [],
};

const statusLabels: Record<TicketStatus, string> = {
  OPEN: "待领取",
  IN_PROGRESS: "处理中",
  RESOLVED: "已解决",
  CLOSED: "已关闭",
};

const category = ref("CAMPUS_NETWORK");
const summary = ref("");
const mode = ref<TicketViewMode>("mine");
const statusFilter = ref("");
const pageNumber = ref(1);
const pageSize = 10;
const ticketPage = ref<{ page: number; size: number; total: number; items: Ticket[] } | null>(null);
const selectedTicket = ref<Ticket | null>(null);
const nextStatus = ref<TicketStatus | "">("");
const loading = ref(false);
const actionId = ref("");
const error = ref("");
const notice = ref("");

const tickets = computed(() => ticketPage.value?.items ?? []);
const pageCount = computed(() => Math.max(1, Math.ceil((ticketPage.value?.total ?? 0) / pageSize)));
const availableTransitions = computed(() => selectedTicket.value
  ? allowedTransitions[selectedTicket.value.status as TicketStatus] ?? []
  : []);

function categoryLabel(value: string) {
  return categories.find((item) => item.value === value)?.label ?? value;
}

function statusLabel(value: string) {
  return statusLabels[value as TicketStatus] ?? value;
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}

function explainError(cause: unknown) {
  if (cause instanceof ApiRequestError) {
    if (cause.status === 401) return "登录已失效或身份令牌无效，请重新登录。";
    if (cause.status === 403) return "当前账号没有此操作的角色权限。请确认登录的是学生、Support Agent 或 Admin 对应账号。";
    if (cause.status === 404) return "没有找到该工单，或当前账号无权查看它。";
    if (cause.status === 409) return "工单状态已被其他操作更新；请刷新列表后重试。";
    if (cause.status === 400 || cause.status === 422) return "请求内容或状态转换不符合业务规则，请检查后重试。";
    if (cause.status >= 500) return "Java 业务服务暂时不可用，请稍后重试。";
  }
  return cause instanceof Error ? cause.message : "工单请求失败。";
}

async function loadTickets() {
  loading.value = true;
  error.value = "";
  notice.value = "";
  try {
    ticketPage.value = mode.value === "mine"
      ? await businessApi.listMyTickets(pageNumber.value, pageSize)
      : await businessApi.listWorkQueue(statusFilter.value, pageNumber.value, pageSize);
    selectedTicket.value = ticketPage.value.items.find((item) => item.id === selectedTicket.value?.id) ?? null;
  } catch (cause) {
    ticketPage.value = null;
    selectedTicket.value = null;
    error.value = explainError(cause);
  } finally {
    loading.value = false;
  }
}

async function createTicket() {
  error.value = "";
  notice.value = "";
  actionId.value = "create";
  try {
    const created = await businessApi.createTicket(category.value, summary.value.trim());
    summary.value = "";
    mode.value = "mine";
    pageNumber.value = 1;
    selectedTicket.value = created;
    notice.value = `工单已创建：${created.id}`;
    await loadTickets();
    selectedTicket.value = created;
  } catch (cause) {
    error.value = explainError(cause);
  } finally {
    actionId.value = "";
  }
}

function selectTicket(ticket: Ticket) {
  selectedTicket.value = ticket;
  nextStatus.value = "";
  error.value = "";
  notice.value = "";
}

async function performTicketAction(ticketId: string, action: "claim" | "close" | "status") {
  error.value = "";
  notice.value = "";
  actionId.value = ticketId;
  try {
    const updated = action === "claim"
      ? await businessApi.claimTicket(ticketId)
      : action === "close"
        ? await businessApi.closeTicket(ticketId)
        : await businessApi.updateTicketStatus(ticketId, nextStatus.value);
    selectedTicket.value = updated;
    nextStatus.value = "";
    notice.value = action === "claim" ? "工单已领取。" : action === "close" ? "工单已关闭。" : "工单状态已更新。";
    await loadTickets();
    selectedTicket.value = updated;
  } catch (cause) {
    error.value = explainError(cause);
  } finally {
    actionId.value = "";
  }
}

async function changeMode(nextMode: TicketViewMode) {
  mode.value = nextMode;
  pageNumber.value = 1;
  selectedTicket.value = null;
  await loadTickets();
}

async function changeQueueFilter() {
  pageNumber.value = 1;
  selectedTicket.value = null;
  await loadTickets();
}

async function movePage(delta: number) {
  const nextPage = pageNumber.value + delta;
  if (nextPage < 1 || nextPage > pageCount.value) return;
  pageNumber.value = nextPage;
  selectedTicket.value = null;
  await loadTickets();
}

onMounted(() => { void loadTickets(); });
</script>

<template>
  <section class="ticket-workbench">
    <p class="eyebrow">Ticket Service</p>
    <h1>校园服务工单</h1>
    <p class="muted">学生查看自己的工单并确认关闭；Support Agent / Admin 处理队列、领取工单并推进状态。所有操作最终由 Java 服务再次做权限与状态校验。</p>

    <div class="ticket-mode-switch" role="tablist" aria-label="工单视图">
      <button type="button" :class="{ active: mode === 'mine' }" @click="changeMode('mine')">我的工单</button>
      <button type="button" :class="{ active: mode === 'queue' }" @click="changeMode('queue')">支持工作队列</button>
    </div>

    <div v-if="mode === 'mine'" class="ticket-create-card form-card">
      <div><h2>提交校园服务请求</h2><p class="muted">创建后会进入 OPEN 状态；工单只对提交人和获授权的支持人员可见。</p></div>
      <form class="ticket-create-form" @submit.prevent="createTicket">
        <label>服务类别
          <select v-model="category">
            <option v-for="item in categories" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label>问题摘要
          <textarea v-model.trim="summary" minlength="1" maxlength="500" required placeholder="描述遇到的问题，不要填写密码或其他敏感凭据。" />
        </label>
        <button type="submit" :disabled="actionId === 'create'">{{ actionId === "create" ? "提交中…" : "提交工单" }}</button>
      </form>
    </div>

    <div class="ticket-list-heading">
      <div><h2>{{ mode === "mine" ? "我的工单记录" : "待处理工单队列" }}</h2><p class="muted">{{ ticketPage ? `共 ${ticketPage.total} 条` : "" }}</p></div>
      <div class="ticket-list-controls">
        <label v-if="mode === 'queue'">状态筛选
          <select v-model="statusFilter" @change="changeQueueFilter">
            <option value="">全部状态</option>
            <option v-for="(label, value) in statusLabels" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <button type="button" class="secondary-button" :disabled="loading" @click="loadTickets">{{ loading ? "加载中…" : "刷新" }}</button>
      </div>
    </div>

    <p v-if="error" class="error-message" role="alert">{{ error }}</p>
    <p v-if="notice" class="success-message" role="status">{{ notice }}</p>
    <div v-if="loading && !ticketPage" class="result-card muted">正在读取工单…</div>
    <div v-else-if="!loading && ticketPage && tickets.length === 0" class="result-card muted">{{ mode === "mine" ? "还没有工单记录。" : "当前筛选条件下没有工单。" }}</div>

    <div v-else-if="tickets.length" class="ticket-content-grid">
      <div class="ticket-list" aria-label="工单列表">
        <button v-for="item in tickets" :key="item.id" type="button" :class="['ticket-list-item', { selected: selectedTicket?.id === item.id }]" @click="selectTicket(item)">
          <span class="ticket-list-top"><strong>{{ categoryLabel(item.category) }}</strong><span :class="['status-pill', `status-${item.status.toLowerCase()}`]">{{ statusLabel(item.status) }}</span></span>
          <span class="ticket-list-summary">{{ item.summary }}</span>
          <small>{{ formatTime(item.submittedAt) }} · v{{ item.version }}</small>
        </button>
        <div class="pagination-controls">
          <button type="button" class="secondary-button" :disabled="pageNumber <= 1 || loading" @click="movePage(-1)">上一页</button>
          <span>第 {{ pageNumber }} / {{ pageCount }} 页</span>
          <button type="button" class="secondary-button" :disabled="pageNumber >= pageCount || loading" @click="movePage(1)">下一页</button>
        </div>
      </div>

      <article v-if="selectedTicket" class="result-card ticket-detail-card">
        <div class="ticket-detail-heading"><div><p class="eyebrow">TICKET DETAIL</p><h2>{{ statusLabel(selectedTicket.status) }} · {{ categoryLabel(selectedTicket.category) }}</h2></div><span class="status-pill">v{{ selectedTicket.version }}</span></div>
        <p>{{ selectedTicket.summary }}</p>
        <dl>
          <dt>工单 ID</dt><dd><code>{{ selectedTicket.id }}</code></dd>
          <dt>提交人</dt><dd>{{ selectedTicket.requesterReference }}</dd>
          <dt>提交时间</dt><dd>{{ formatTime(selectedTicket.submittedAt) }}</dd>
          <dt>处理人</dt><dd>{{ selectedTicket.assigneeReference ?? "尚未领取" }}</dd>
          <dt>领取时间</dt><dd>{{ formatTime(selectedTicket.claimedAt) }}</dd>
        </dl>

        <div v-if="mode === 'mine' && selectedTicket.status === 'RESOLVED'" class="ticket-action-row">
          <p class="muted">支持人员已标记解决。确认问题已处理后，可以关闭工单。</p>
          <button type="button" :disabled="actionId === selectedTicket.id" @click="performTicketAction(selectedTicket.id, 'close')">{{ actionId === selectedTicket.id ? "处理中…" : "确认并关闭" }}</button>
        </div>

        <div v-if="mode === 'queue'" class="ticket-action-row">
          <button v-if="selectedTicket.status === 'OPEN' && !selectedTicket.assigneeReference" type="button" :disabled="actionId === selectedTicket.id" @click="performTicketAction(selectedTicket.id, 'claim')">领取工单</button>
          <div v-if="availableTransitions.length" class="status-action">
            <label>推进状态
              <select v-model="nextStatus">
                <option value="" disabled>选择目标状态</option>
                <option v-for="target in availableTransitions" :key="target" :value="target">{{ statusLabel(target) }}</option>
              </select>
            </label>
            <button type="button" :disabled="!nextStatus || actionId === selectedTicket.id" @click="performTicketAction(selectedTicket.id, 'status')">更新状态</button>
          </div>
          <p class="muted">Support Agent 只能更新自己领取的工单；Admin 可按权限处理。非法状态转换或并发版本冲突会由服务端拒绝。</p>
        </div>
      </article>
      <aside v-else class="result-card muted ticket-detail-placeholder">选择一条工单，查看其状态、负责人和可执行操作。</aside>
    </div>
  </section>
</template>
