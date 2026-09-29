function requiredBaseUrl(name: "VITE_AGENT_API_BASE_URL" | "VITE_BUSINESS_API_BASE_URL"): string {
  const value = import.meta.env[name]?.trim();
  if (!value) {
    throw new Error(`${name} is required; copy .env.example to .env.local first`);
  }
  return value.replace(/\/$/, "");
}

export const environment = {
  agentApiBaseUrl: requiredBaseUrl("VITE_AGENT_API_BASE_URL"),
  businessApiBaseUrl: requiredBaseUrl("VITE_BUSINESS_API_BASE_URL"),
} as const;
