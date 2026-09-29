<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { businessApi } from "@/api/business";
import { session } from "@/session/session";

const username = ref("");
const password = ref("");
const error = ref<string | null>(null);
const submitting = ref(false);
const router = useRouter();
const route = useRoute();

async function login() {
  error.value = null;
  submitting.value = true;
  try {
    const result = await businessApi.login(username.value, password.value);
    session.start(result.accessToken, result.expiresAt);
    await router.push(typeof route.query.redirect === "string" ? route.query.redirect : "/");
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "登录请求未完成";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="narrow-section">
    <p class="eyebrow">Authentication</p>
    <h1>登录</h1>
    <form class="form-card" @submit.prevent="login">
      <label>用户名<input v-model.trim="username" autocomplete="username" required /></label>
      <label>密码<input v-model="password" type="password" autocomplete="current-password" required /></label>
      <p v-if="error" class="error-message">{{ error }}</p>
      <button :disabled="submitting" type="submit">{{ submitting ? "正在登录" : "登录" }}</button>
    </form>
  </section>
</template>
