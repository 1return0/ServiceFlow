package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.fail;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.ticket.dto.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.entity.TicketEventInboxEntity;
import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.enums.OperatorRole;
import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import com.serviceflow.business.ticket.enums.TicketStatus;
import com.serviceflow.business.ticket.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.mapper.TicketMapper;
import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.outbox.TicketOutboxDeliveryService;
import com.serviceflow.business.ticket.service.TicketService;

/**
 * Opt-in business-chain smoke. Scheduler stays disabled, while one explicitly
 * selected Outbox event travels through the real publisher and consumer.
 */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = {
                "spring.autoconfigure.exclude=",
                "eduops.messaging.ticket-events.enabled=true",
                "eduops.outbox.delivery.enabled=true",
                "eduops.outbox.delivery.scheduler-enabled=false",
                "eduops.outbox.inbox.enabled=true"
        }
)
@ActiveProfiles("local")
@EnabledIfSystemProperty(
        named = "runTicketStatusOutboxToInboxIntegrationTests",
        matches = "true"
)
class TicketStatusOutboxToInboxIntegrationTest {

    @Autowired
    private TicketService ticketService;

    @Autowired
    private TicketMapper ticketMapper;

    @Autowired
    private TicketOutboxEventMapper outboxMapper;

    @Autowired
    private TicketEventInboxMapper inboxMapper;

    @Autowired
    private TicketNotificationMapper notificationMapper;

    @Autowired
    private TicketOutboxDeliveryService deliveryService;

    private UUID ticketId;
    private UUID eventId;

    @AfterEach
    void cleanUp() {
        if (eventId != null) {
            inboxMapper.deleteById(eventId);
            notificationMapper.delete(
                    Wrappers.<TicketNotificationEntity>lambdaQuery()
                            .eq(TicketNotificationEntity::getEventId, eventId)
            );
            outboxMapper.deleteById(eventId);
        }
        if (ticketId != null) {
            ticketMapper.deleteById(ticketId);
        }
    }

    @Test
    void delivers_a_real_ticket_status_change_from_outbox_to_inbox()
            throws InterruptedException {
        var created = ticketService.createTicket(
                "outbox-inbox-smoke-" + UUID.randomUUID(),
                new CreateTicketRequest(
                ServiceRequestCategory.CAMPUS_NETWORK,
                "Verify the status-change event delivery chain"
        ));
        ticketId = created.id();

        ticketService.updateTicketStatus(
                ticketId,
                new UpdateTicketStatusRequest(TicketStatus.IN_PROGRESS),
                OperatorRole.SUPPORT_AGENT
        );

        TicketOutboxEventEntity event = outboxMapper.selectOne(
                Wrappers.<TicketOutboxEventEntity>lambdaQuery()
                        .eq(TicketOutboxEventEntity::getAggregateId, ticketId)
        );
        assertThat(event).isNotNull();
        eventId = event.getId();
        assertThat(event.getPublishedAt()).isNull();

        boolean delivered = deliveryService.deliverEventById(eventId);
        awaitInboxRow();

        TicketOutboxEventEntity deliveredEvent = outboxMapper.selectById(eventId);
        assertThat(delivered).isTrue();
        assertThat(deliveredEvent.getPublishedAt()).isNotNull();
        assertThat(deliveredEvent.getPublishAttempts()).isEqualTo(1);
        assertThat(notificationMapper.selectCount(
                Wrappers.<TicketNotificationEntity>lambdaQuery()
                        .eq(TicketNotificationEntity::getEventId, eventId)
        )).isEqualTo(1L);
    }

    private void awaitInboxRow() throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(5));
        while (Instant.now().isBefore(deadline)) {
            TicketEventInboxEntity inboxEvent = inboxMapper.selectById(eventId);
            if (inboxEvent != null) {
                assertThat(inboxEvent.getEventType())
                        .isEqualTo("ticket.status_changed.v1");
                return;
            }
            Thread.sleep(100);
        }
        fail("consumer did not persist the ticket status event within five seconds");
    }
}
