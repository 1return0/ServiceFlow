import { createApiClient } from "./http";
import { environment } from "@/config/environment";
import { session } from "@/session/session";

// 第 2 课接入登录会话后，把 tokenProvider 注入到这两个 Client；页面不直接拼 Authorization。
export const agentApiClient = createApiClient(environment.agentApiBaseUrl, session.accessToken);
export const businessApiClient = createApiClient(environment.businessApiBaseUrl, session.accessToken);
