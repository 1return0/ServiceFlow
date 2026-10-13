<script setup lang="ts">
import ReportWorkspace from "@/components/ReportWorkspace.vue";
import { environment } from "@/config/environment";
import { session } from "@/session/session";
</script>
<template><ReportWorkspace base-path="/api/v1/knowledge/reports" :base-url="environment.agentApiBaseUrl" :token-provider="session.accessToken" query-placeholder="例如：依据校园公开指南，整理校园网络访问步骤" /></template>
