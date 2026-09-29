import type {
  HandoffTask,
  LoginResponse,
  Notification,
  NotificationSummary,
  PageResponse,
  ResultEnvelope,
  Ticket,
} from "./contracts";
import { businessApiClient } from "./clients";

function unwrap<T>(result: ResultEnvelope<T>): T {
  if (result.code !== 0) {
    throw new Error(result.message || "Business request was not accepted");
  }
  return result.data;
}

export const businessApi = {
  async login(username: string, password: string) {
    return unwrap(await businessApiClient.post<ResultEnvelope<LoginResponse>>("/api/v1/auth/login", { username, password }));
  },
  async createTicket(category: string, summary: string) {
    return unwrap(await businessApiClient.post<ResultEnvelope<Ticket>>("/api/v1/tickets", { category, summary }));
  },
  async listMyTickets(page = 1, size = 10) {
    return unwrap(await businessApiClient.get<ResultEnvelope<PageResponse<Ticket>>>(`/api/v1/tickets/me?page=${page}&size=${size}`));
  },
  async listWorkQueue(status: string, page = 1, size = 10) {
    const query = new URLSearchParams({ page: String(page), size: String(size) });
    if (status) query.set("status", status);
    return unwrap(await businessApiClient.get<ResultEnvelope<PageResponse<Ticket>>>(`/api/v1/tickets?${query.toString()}`));
  },
  async claimTicket(ticketId: string) {
    return unwrap(await businessApiClient.patch<ResultEnvelope<Ticket>>(`/api/v1/tickets/${ticketId}/claim`));
  },
  async updateTicketStatus(ticketId: string, targetStatus: string) {
    return unwrap(await businessApiClient.patch<ResultEnvelope<Ticket>>(`/api/v1/tickets/${ticketId}/status`, { targetStatus }));
  },
  async closeTicket(ticketId: string) {
    return unwrap(await businessApiClient.patch<ResultEnvelope<Ticket>>(`/api/v1/tickets/${ticketId}/close`));
  },
  async getTicket(ticketId: string) {
    return unwrap(await businessApiClient.get<ResultEnvelope<Ticket>>(`/api/v1/tickets/${ticketId}`));
  },
  async listNotifications() {
    return unwrap(await businessApiClient.get<ResultEnvelope<Notification[]>>("/api/v1/notifications/me"));
  },
  async notificationSummary() {
    return unwrap(await businessApiClient.get<ResultEnvelope<NotificationSummary>>("/api/v1/notifications/me/summary"));
  },
  async markNotificationRead(notificationId: string) {
    return unwrap(await businessApiClient.patch<ResultEnvelope<Notification>>(`/api/v1/notifications/${notificationId}/read`));
  },
  async listOpenHandoffs() {
    return unwrap(await businessApiClient.get<ResultEnvelope<HandoffTask[]>>("/api/v1/handoffs/admin"));
  },
  async claimHandoff(taskId: string) {
    return unwrap(await businessApiClient.patch<ResultEnvelope<HandoffTask>>(`/api/v1/handoffs/${taskId}/claim`));
  },
  async resolveHandoff(taskId: string) {
    return unwrap(await businessApiClient.patch<ResultEnvelope<HandoffTask>>(`/api/v1/handoffs/${taskId}/resolve`));
  },
};
