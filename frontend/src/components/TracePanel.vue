<script setup lang="ts">
import type { CoordinatorTrace } from "@/api/contracts";

defineProps<{ trace: CoordinatorTrace }>();
</script>

<template>
  <section class="trace-panel">
    <h2>Coordinator Trace</h2>
    <p class="muted">request_id: {{ trace.request_id }}</p>
    <ol>
      <li v-for="(step, index) in trace.steps" :key="`${step.node}-${index}`">
        <strong>{{ step.node }}</strong>
        <span>{{ step.status }} · {{ Math.round(step.elapsed_seconds * 1000) }} ms</span>
        <small v-if="step.specialist_identity">{{ step.specialist_identity }}</small>
        <small v-if="step.tool_name">tool: {{ step.tool_name }}</small>
        <small v-if="step.failure_code" class="error-message">{{ step.failure_code }}</small>
      </li>
    </ol>
  </section>
</template>
