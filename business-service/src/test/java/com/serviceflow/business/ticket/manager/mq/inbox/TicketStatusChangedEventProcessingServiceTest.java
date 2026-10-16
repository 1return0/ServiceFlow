package com.serviceflow.business.ticket.manager.mq.inbox;

import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

class TicketStatusChangedEventProcessingServiceTest {

    private final TicketEventInboxService inboxService = Mockito.mock(
            TicketEventInboxService.class
    );
    private final TicketStatusNotificationService notificationService = Mockito.mock(
            TicketStatusNotificationService.class
    );
    private final TicketStatusChangedEventProcessingService service =
            new TicketStatusChangedEventProcessingService(inboxService, notificationService);

    @Test
    void creates_one_notification_after_a_first_delivery_is_recorded() {
        TicketEventInboxMessage event = event();
        when(inboxService.recordIfFirstSeen(event))
                .thenReturn(TicketEventInboxRecordResult.firstDeliveryRecorded());

        service.process(event);

        verify(notificationService).createForStatusChange(event);
    }

    @Test
    void skips_the_business_effect_for_an_already_recorded_redelivery() {
        TicketEventInboxMessage event = event();
        when(inboxService.recordIfFirstSeen(event))
                .thenReturn(TicketEventInboxRecordResult.alreadyProcessed());

        service.process(event);

        verify(notificationService, never()).createForStatusChange(event);
    }

    private static TicketEventInboxMessage event() {
        UUID ticketId = UUID.fromString("22222222-2222-2222-2222-222222222222");
        return new TicketEventInboxMessage(
                UUID.fromString("11111111-1111-1111-1111-111111111111"),
                "ticket.status_changed.v1",
                "ticket",
                ticketId,
                "{\"ticketId\":\"" + ticketId
                        + "\",\"requesterReference\":\"student-001\""
                        + ",\"status\":\"RESOLVED\",\"version\":1}"
        );
    }
}
