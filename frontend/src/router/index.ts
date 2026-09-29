import { createRouter, createWebHistory } from "vue-router";

import HomeView from "@/views/HomeView.vue";
import EvidenceView from "@/views/EvidenceView.vue";
import HandoffView from "@/views/HandoffView.vue";
import KnowledgeImportView from "@/views/KnowledgeImportView.vue";
import LoginView from "@/views/LoginView.vue";
import NotificationsView from "@/views/NotificationsView.vue";
import TicketView from "@/views/TicketView.vue";
import TriageView from "@/views/TriageView.vue";
import { session } from "@/session/session";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/login", name: "login", component: LoginView },
    { path: "/tickets", name: "tickets", component: TicketView, meta: { requiresAuth: true } },
    { path: "/notifications", name: "notifications", component: NotificationsView, meta: { requiresAuth: true } },
    { path: "/assistant", name: "assistant", component: TriageView, meta: { requiresAuth: true } },
    { path: "/knowledge/imports", name: "knowledge-imports", component: KnowledgeImportView },
    { path: "/handoffs", name: "handoffs", component: HandoffView, meta: { requiresAuth: true } },
    { path: "/evidence", name: "evidence", component: EvidenceView },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !session.isAuthenticated.value) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
