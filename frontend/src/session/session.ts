import { computed, ref } from "vue";

const STORAGE_KEY = "serviceflow.access-token";
const token = ref<string | null>(sessionStorage.getItem(STORAGE_KEY));
const expiresAt = ref<string | null>(sessionStorage.getItem("serviceflow.token-expires-at"));

export const session = {
  isAuthenticated: computed(() => token.value !== null),
  expiresAt: computed(() => expiresAt.value),
  accessToken: () => token.value,
  start(accessToken: string, nextExpiresAt: string) {
    token.value = accessToken;
    expiresAt.value = nextExpiresAt;
    sessionStorage.setItem(STORAGE_KEY, accessToken);
    sessionStorage.setItem("serviceflow.token-expires-at", nextExpiresAt);
  },
  clear() {
    token.value = null;
    expiresAt.value = null;
    sessionStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem("serviceflow.token-expires-at");
  },
};
