package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.fail;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.ticket.dao.entity.TicketEventInboxEntity;
import com.serviceflow.business.ticket.dao.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketNotificationMapper;

/**
 * Opt-in end-to-end smoke: RabbitMQ routes an event to @RabbitListener and the
 * consumer writes exactly one Inbox row. The Outbox scheduler stays disabled.
 */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = {
                "spring.autoconfigure.exclude=",
                "eduops.messaging.ticket-events.enabled=true",
                "eduops.outbox.delivery.enabled=false",
                "eduops.outbox.inbox.enabled=true"
        }
)
@ActiveProfiles("local")
@EnabledIfSystemProperty(
        named = "runRabbitMqInboxIntegrationTests",
        matches = "true"
)
class TicketEventInboxRabbitMqPostgresIntegrationTest {

    private static final String EXCHANGE = "eduops.ticket.events";
    private static final String ROUTING_KEY = "ticket.status.changed.v1";
    private static final String QUEUE = "eduops.ticket.status-events.v1";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private TicketEventInboxMapper inboxMapper;

    @Autowired
    private TicketNotificationMapper notificationMapper;

    private UUID testEventId;

    @AfterEach
    void cleanUpInboxRow() {
        if (testEventId != null) {
            inboxMapper.deleteById(testEventId);
            notificationMapper.delete(
                    Wrappers.<TicketNotificationEntity>lambdaQuery()
                            .eq(TicketNotificationEntity::getEventId, testEventId)
            );
        }
    }

    @Test
    void routes_a_message_to_the_real_consumer_and_persists_one_inbox_row()
            throws InterruptedException {
        testEventId = UUID.randomUUID();
        UUID ticketId = UUID.randomUUID();

        publishTicketStatusChanged(testEventId, ticketId);
        awaitInboxRow();

        publishTicketStatusChanged(testEventId, ticketId);
        awaitQueueToDrain();

        Long rowCount = inboxMapper.selectCount(
                Wrappers.<TicketEventInboxEntity>lambdaQuery()
                        .eq(TicketEventInboxEntity::getEventId, testEventId)
        );
        assertThat(rowCount).isEqualTo(1L);
        assertThat(notificationMapper.selectCount(
                Wrappers.<TicketNotificationEntity>lambdaQuery()
                        .eq(TicketNotificationEntity::getEventId, testEventId)
        )).isEqualTo(1L);
    }

    private void publishTicketStatusChanged(UUID eventId, UUID ticketId) {
        rabbitTemplate.convertAndSend(
                EXCHANGE,
                ROUTING_KEY,
                "{\"ticketId\":\"" + ticketId
                        + "\",\"requesterReference\":\"rabbit-smoke-student\""
                        + ",\"status\":\"RESOLVED\",\"version\":1}",
                message -> {
                    MessageProperties properties = message.getMessageProperties();
                    properties.setContentType(MessageProperties.CONTENT_TYPE_JSON);
                    properties.setHeader("eventId", eventId.toString());
                    properties.setHeader("eventType", "ticket.status_changed.v1");
                    properties.setHeader("aggregateType", "ticket");
                    properties.setHeader("aggregateId", ticketId.toString());
                    return message;
                }
        );
    }

    private void awaitInboxRow() throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(5));
        while (Instant.now().isBefore(deadline)) {
            if (inboxMapper.selectById(testEventId) != null) {
                return;
            }
            Thread.sleep(100);
        }
        fail("consumer did not persist the RabbitMQ event within five seconds");
    }

    private void awaitQueueToDrain() throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(5));
        while (Instant.now().isBefore(deadline)) {
            Integer messageCount = rabbitTemplate.execute(channel ->
                    channel.queueDeclarePassive(QUEUE).getMessageCount()
            );
            if (messageCount != null && messageCount == 0) {
                return;
            }
            Thread.sleep(100);
        }
        fail("RabbitMQ queue did not drain within five seconds");
    }
}
