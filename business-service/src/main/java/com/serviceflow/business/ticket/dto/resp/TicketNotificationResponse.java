package com.serviceflow.business.ticket.dto.resp;

import java.time.Instant;
import java.util.UUID;

import com.serviceflow.business.ticket.dao.entity.TicketNotificationEntity;

/** Student-safe projection: it deliberately excludes internal event payloads. */
public record TicketNotificationResponse(
        UUID id,
        UUID ticketId,
        String notificationType,
        String message,
        Instant createdAt,
        Instant readAt
) {

    public static TicketNotificationResponse from(TicketNotificationEntity entity) {
        return new TicketNotificationResponse(
                entity.getId(),
                entity.getTicketId(),
                entity.getNotificationType(),
                entity.getMessage(),
                entity.getCreatedAt(),
                entity.getReadAt()
        );
    }
}
