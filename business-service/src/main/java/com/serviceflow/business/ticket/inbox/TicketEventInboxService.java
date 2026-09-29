package com.serviceflow.business.ticket.inbox;

import java.time.Instant;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.serviceflow.business.ticket.entity.TicketEventInboxEntity;
import com.serviceflow.business.ticket.mapper.TicketEventInboxMapper;
import lombok.RequiredArgsConstructor;

/**
 * Inbox Pattern: PostgreSQL's primary-key constraint is the final idempotency
 * guard. ON CONFLICT avoids aborting the transaction on a redelivery.
 */
@Service
@RequiredArgsConstructor
public class TicketEventInboxService {

    private final TicketEventInboxMapper inboxMapper;

    @Transactional
    public TicketEventInboxRecordResult recordIfFirstSeen(
            TicketEventInboxMessage message
    ) {
        TicketEventInboxEntity entity = new TicketEventInboxEntity(
                message.eventId(),
                message.eventType(),
                message.aggregateType(),
                message.aggregateId(),
                message.payload(),
                Instant.now()
        );
        int affectedRows = inboxMapper.insertIfAbsent(entity);
        if (affectedRows == 1) {
            return TicketEventInboxRecordResult.firstDeliveryRecorded();
        }
        if (affectedRows == 0) {
            return TicketEventInboxRecordResult.alreadyProcessed();
        }
        throw new IllegalStateException(
                "ticket inbox insert returned an unexpected row count: "
                        + affectedRows
        );
    }
}
