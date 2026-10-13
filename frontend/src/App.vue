<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from "vue-router";
import { session } from "@/session/session";

const router = useRouter();

function logout() {
  session.clear();
  void router.push("/login");
}
</script>

<template>
  <header class="app-header">
    <RouterLink class="brand" to="/">ServiceFlow</RouterLink>
    <nav aria-label="主导航">
      <RouterLink to="/tickets">工单</RouterLink>
      <RouterLink to="/notifications">通知</RouterLink>
      <RouterLink to="/assistant">协同助手</RouterLink>
      <RouterLink to="/knowledge/imports">知识导入</RouterLink>
      <RouterLink to="/reports">知识报告</RouterLink>
      <RouterLink to="/handoffs">人工交接</RouterLink>
      <RouterLink to="/evidence">验证边界</RouterLink>
      <RouterLink v-if="!session.isAuthenticated.value" to="/login">登录</RouterLink>
      <button v-else class="text-button" type="button" @click="logout">退出</button>
    </nav>
  </header>
  <main class="app-main">
    <RouterView />
  </main>
</template>
