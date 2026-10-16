package com.serviceflow.business.ticket.manager.mq.inbox;

import java.util.UUID;

/** Normalized data read from a RabbitMQ message before it reaches the database. */
public record TicketEventInboxMessage(
        UUID eventId,
        String eventType,
        String aggregateType,
        UUID aggregateId,
        String payload
) {

    public TicketEventInboxMessage {
        if (eventId == null || aggregateId == null) {
            throw new IllegalArgumentException("event and aggregate ids are required");
        }
        if (isBlank(eventType) || isBlank(aggregateType) || isBlank(payload)) {
            throw new IllegalArgumentException("event message fields must be non-blank");
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
