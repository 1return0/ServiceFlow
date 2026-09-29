package com.serviceflow.business.ticket.vo;

import java.time.Instant;
import java.util.UUID;

import com.serviceflow.business.ticket.entity.TicketEntity;
import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import com.serviceflow.business.ticket.enums.TicketStatus;

/** Response VO: exposes the ticket representation owned by the API contract. */
public record TicketResponse(
        UUID id,
        String requesterReference,
        ServiceRequestCategory category,
        String summary,
        Instant submittedAt,
        TicketStatus status,
        String assigneeReference,
        Instant claimedAt,
        Long version
) {
    public static TicketResponse from(TicketEntity entity) {
        return new TicketResponse(
                entity.getId(),
                entity.getRequesterReference(),
                entity.getCategory(),
                entity.getSummary(),
                entity.getSubmittedAt(),
                entity.getStatus(),
                entity.getAssigneeReference(),
                entity.getClaimedAt(),
                entity.getVersion()
        );
    }
}
