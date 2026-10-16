package com.serviceflow.business.ticket.manager.mq.outbox;

import org.springframework.scheduling.annotation.Scheduled;

/** Trigger only: delivery rules remain inside TicketOutboxDeliveryService. */
public class TicketOutboxDeliveryScheduler {

    private final TicketOutboxDeliveryService deliveryService;
    private final int batchSize;

    public TicketOutboxDeliveryScheduler(
            TicketOutboxDeliveryService deliveryService,
            int batchSize
    ) {
        if (batchSize < 1 || batchSize > 100) {
            throw new IllegalArgumentException("outbox batch size must be between 1 and 100");
        }
        this.deliveryService = deliveryService;
        this.batchSize = batchSize;
    }

    @Scheduled(fixedDelayString = "${eduops.outbox.delivery.fixed-delay-ms:10000}")
    public void deliverPendingEvents() {
        deliveryService.deliverNextBatch(batchSize);
    }
}
