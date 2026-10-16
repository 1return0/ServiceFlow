package com.serviceflow.business.ticket.manager.mq.outbox;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import org.junit.jupiter.api.Test;

class TicketOutboxDeliverySchedulerTest {

    @Test
    void delegates_each_scheduled_run_to_the_delivery_service() {
        TicketOutboxDeliveryService deliveryService = mock(TicketOutboxDeliveryService.class);
        TicketOutboxDeliveryScheduler scheduler = new TicketOutboxDeliveryScheduler(
                deliveryService,
                20
        );

        scheduler.deliverPendingEvents();

        verify(deliveryService).deliverNextBatch(20);
    }
}
