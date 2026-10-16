package com.serviceflow.business.ticket.manager.mq.event;

import java.util.UUID;

import com.serviceflow.business.ticket.domain.TicketStatus;

/** Immutable business snapshot carried by a ticket.status_changed.v1 event. */
public record TicketStatusChangedEventPayload(
        UUID ticketId,
        String requesterReference,
        TicketStatus status,
        long version
) {

    public TicketStatusChangedEventPayload {
        if (ticketId == null || status == null || requesterReference == null
                || requesterReference.isBlank()) {
            throw new IllegalArgumentException(
                    "ticket status event payload fields must be present"
            );
        }
        requesterReference = requesterReference.trim();
        if (version < 0) {
            throw new IllegalArgumentException(
                    "ticket status event version must not be negative"
            );
        }
    }
}
