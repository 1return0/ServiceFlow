package com.serviceflow.business.ticket.inbox;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;

/**
 * Keeps durable receipt and its business effect in one transaction. If the
 * notification write fails, the Inbox row rolls back too, so redelivery can retry
 * the whole effect instead of being mistaken for an already handled event.
 */
@Service
@RequiredArgsConstructor
public class TicketStatusChangedEventProcessingService {

    private final TicketEventInboxService inboxService;
    private final TicketStatusNotificationService notificationService;

    @Transactional
    public void process(TicketEventInboxMessage event) {
        TicketEventInboxRecordResult receipt = inboxService.recordIfFirstSeen(event);
        if (!receipt.created()) {
            return;
        }
        notificationService.createForStatusChange(event);
    }
}
