package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doThrow;

import java.util.UUID;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.ActiveProfiles;

import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketEventInboxMessage;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketEventInboxService;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketStatusChangedEventProcessingService;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketStatusNotificationService;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;

/**
 * Opt-in PostgreSQL verification of the Consumer's all-or-nothing business
 * transaction. The notification writer is deliberately failed after Inbox insert.
 */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = {
                "spring.autoconfigure.exclude=",
                "eduops.outbox.delivery.enabled=false",
                "eduops.outbox.inbox.enabled=false"
        }
)
@ActiveProfiles("local")
@EnabledIfSystemProperty(
        named = "runPostgresNotificationTransactionIntegrationTests",
        matches = "true"
)
class TicketStatusChangedEventProcessingPostgresIntegrationTest {

    @Autowired
    private TicketStatusChangedEventProcessingService processingService;

    @Autowired
    private TicketEventInboxMapper inboxMapper;

    @MockitoBean
    private TicketStatusNotificationService notificationService;

    private UUID eventId;

    @AfterEach
    void cleanUp() {
        if (eventId != null) {
            inboxMapper.deleteById(eventId);
        }
    }

    @Test
    void rolls_back_the_inbox_receipt_when_notification_writing_fails() {
        eventId = UUID.randomUUID();
        TicketEventInboxMessage event = statusChangedEvent(eventId);
        doThrow(new IllegalStateException("notification database temporarily unavailable"))
                .when(notificationService)
                .createForStatusChange(event);

        assertThatThrownBy(() -> processingService.process(event))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("notification database temporarily unavailable");

        assertThat(inboxMapper.selectById(eventId)).isNull();
    }

    private static TicketEventInboxMessage statusChangedEvent(UUID eventId) {
        UUID ticketId = UUID.randomUUID();
        return new TicketEventInboxMessage(
                eventId,
                "ticket.status_changed.v1",
                "ticket",
                ticketId,
                "{\"ticketId\":\"" + ticketId
                        + "\",\"requesterReference\":\"transaction-smoke-student\""
                        + ",\"status\":\"RESOLVED\",\"version\":1}"
        );
    }
}
