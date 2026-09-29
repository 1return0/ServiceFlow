package com.serviceflow.business.ticket.outbox;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;

/**
 * Claims events in a short database statement, publishes outside a DB transaction,
 * then acknowledges only with the same lease token.
 */
public class TicketOutboxDeliveryService {

    private static final Duration LEASE_DURATION = Duration.ofSeconds(30);

    private final TicketOutboxEventMapper eventMapper;
    private final TicketOutboxEventPublisher publisher;
    private final Clock clock;

    public TicketOutboxDeliveryService(
            TicketOutboxEventMapper eventMapper,
            TicketOutboxEventPublisher publisher,
            Clock clock
    ) {
        this.eventMapper = eventMapper;
        this.publisher = publisher;
        this.clock = clock;
    }

    public int deliverNextBatch(int limit) {
        if (limit < 1 || limit > 100) {
            throw new IllegalArgumentException("delivery limit must be between 1 and 100");
        }

        Instant now = clock.instant();
        UUID leaseToken = UUID.randomUUID();
        List<TicketOutboxEventEntity> events = eventMapper.claimNextUnpublished(
                limit,
                now,
                leaseToken,
                now.plus(LEASE_DURATION)
        );

        int published = 0;
        for (TicketOutboxEventEntity event : events) {
            try {
                publisher.publish(event);
                published += eventMapper.markPublished(
                        event.getId(),
                        leaseToken,
                        clock.instant()
                );
            } catch (RuntimeException error) {
                eventMapper.releaseAfterFailure(
                        event.getId(),
                        leaseToken,
                        "outbox-publisher-failed"
                );
            }
        }
        return published;
    }

    /**
     * Delivers one known event without claiming unrelated backlog entries.
     * Useful for an operator-driven repair or a tightly scoped integration test.
     */
    public boolean deliverEventById(UUID eventId) {
        if (eventId == null) {
            throw new IllegalArgumentException("event id is required");
        }
        Instant now = clock.instant();
        UUID leaseToken = UUID.randomUUID();
        TicketOutboxEventEntity event = eventMapper.claimById(
                eventId,
                now,
                leaseToken,
                now.plus(LEASE_DURATION)
        );
        if (event == null) {
            return false;
        }
        try {
            publisher.publish(event);
            return eventMapper.markPublished(
                    event.getId(),
                    leaseToken,
                    clock.instant()
            ) == 1;
        } catch (RuntimeException error) {
            eventMapper.releaseAfterFailure(
                    event.getId(),
                    leaseToken,
                    "outbox-publisher-failed"
            );
            return false;
        }
    }
}
