package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.amqp.core.AmqpAdmin;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

import com.serviceflow.business.ticket.config.TicketEventRabbitMqTopologyConfiguration;
import com.serviceflow.business.ticket.config.TicketEventConsumerReliabilityConfiguration;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketEventInboxMessage;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketStatusChangedEventProcessingService;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketStatusChangedInboxConsumer;

/**
 * Opt-in real-broker verification: a temporary Consumer failure is retried three
 * times with the configured backoff before its message is routed to a test-only DLQ.
 */
@SpringBootTest(
        classes = TicketEventInboxTransientFailureRabbitMqIntegrationTest.TransientRetryTestApplication.class,
        properties = {
                "spring.main.web-application-type=none",
                "eduops.messaging.ticket-events.enabled=true",
                "eduops.messaging.ticket-events.exchange=eduops.test.ticket.events.retry",
                "eduops.messaging.ticket-events.queue=eduops.test.ticket.status-events.retry",
                "eduops.messaging.ticket-events.routing-key=test.ticket.status.changed.retry.v1",
                "eduops.messaging.ticket-events.dead-letter-exchange=eduops.test.ticket.events.retry.dead",
                "eduops.messaging.ticket-events.dead-letter-queue=eduops.test.ticket.status-events.retry.dead",
                "eduops.messaging.ticket-events.dead-letter-routing-key=test.ticket.status.changed.retry.dlq.v1",
                "eduops.outbox.delivery.enabled=false",
                "eduops.outbox.inbox.enabled=true"
        }
)
@ActiveProfiles("local")
@EnabledIfSystemProperty(
        named = "runRabbitMqTransientRetryIntegrationTests",
        matches = "true"
)
class TicketEventInboxTransientFailureRabbitMqIntegrationTest {

    private static final String EXCHANGE = "eduops.test.ticket.events.retry";
    private static final String ROUTING_KEY = "test.ticket.status.changed.retry.v1";
    private static final String MAIN_QUEUE = "eduops.test.ticket.status-events.retry";
    private static final String DEAD_LETTER_QUEUE = "eduops.test.ticket.status-events.retry.dead";
    private static final String DEAD_LETTER_EXCHANGE = "eduops.test.ticket.events.retry.dead";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private AmqpAdmin amqpAdmin;

    @MockitoBean
    private TicketStatusChangedEventProcessingService processingService;

    @AfterEach
    void cleanUpDedicatedTestTopology() {
        amqpAdmin.deleteQueue(MAIN_QUEUE);
        amqpAdmin.deleteQueue(DEAD_LETTER_QUEUE);
        amqpAdmin.deleteExchange(EXCHANGE);
        amqpAdmin.deleteExchange(DEAD_LETTER_EXCHANGE);
    }

    @Test
    void retries_a_temporary_failure_three_times_then_routes_the_message_to_the_dlq()
            throws InterruptedException {
        UUID eventId = UUID.randomUUID();
        UUID ticketId = UUID.randomUUID();
        String body = "temporary-failure-event-" + eventId;
        doThrow(new IllegalStateException("temporary database outage"))
                .when(processingService)
                .process(any(TicketEventInboxMessage.class));

        rabbitTemplate.convertAndSend(EXCHANGE, ROUTING_KEY, body, message -> {
            MessageProperties properties = message.getMessageProperties();
            properties.setHeader("eventId", eventId.toString());
            properties.setHeader("eventType", "ticket.status_changed.v1");
            properties.setHeader("aggregateType", "ticket");
            properties.setHeader("aggregateId", ticketId.toString());
            return message;
        });

        Message deadLettered = awaitDeadLetteredMessage();

        verify(processingService, timeout(1_000).times(3))
                .process(any(TicketEventInboxMessage.class));
        assertThat(new String(deadLettered.getBody(), StandardCharsets.UTF_8)).isEqualTo(body);
    }

    private Message awaitDeadLetteredMessage() throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(12));
        while (Instant.now().isBefore(deadline)) {
            Message message = rabbitTemplate.receive(DEAD_LETTER_QUEUE, 250);
            if (message != null) {
                return message;
            }
            Thread.sleep(100);
        }
        throw new AssertionError("temporary failure did not arrive in the dedicated dead-letter queue");
    }

    @SpringBootConfiguration
    @EnableAutoConfiguration
    @Import({
            TicketEventRabbitMqTopologyConfiguration.class,
            TicketEventConsumerReliabilityConfiguration.class,
            TicketStatusChangedInboxConsumer.class
    })
    static class TransientRetryTestApplication {
    }
}
