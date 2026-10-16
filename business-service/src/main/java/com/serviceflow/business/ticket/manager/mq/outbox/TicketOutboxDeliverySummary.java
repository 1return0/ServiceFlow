package com.serviceflow.business.ticket.manager.mq.outbox;

import java.time.Instant;

/**
 * Safe operational view: it exposes delivery health without exposing ticket content
 * or the event payload.
 */
public record TicketOutboxDeliverySummary(
        long pendingEvents,
        long activelyLeasedEvents,
        long retryableFailedEvents,
        Instant oldestPendingCreatedAt
) {
}
