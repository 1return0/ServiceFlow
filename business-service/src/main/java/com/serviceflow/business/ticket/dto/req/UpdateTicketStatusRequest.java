package com.serviceflow.business.ticket.dto.req;

import com.serviceflow.business.ticket.domain.TicketStatus;
import jakarta.validation.constraints.NotNull;

/** The requested target state. Java validates the actual transition separately. */
public record UpdateTicketStatusRequest(@NotNull TicketStatus targetStatus) {
}
