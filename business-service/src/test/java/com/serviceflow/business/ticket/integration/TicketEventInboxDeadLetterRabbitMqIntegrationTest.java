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
import org.springframework.amqp.core.AmqpAdmin;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import com.serviceflow.business.ServiceFlowBusinessApplication;

/**
 * Opt-in real-broker verification: a malformed event is permanently invalid, so
 * the Consumer rejects it directly into a dedicated temporary-test DLQ.
 */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = {
                "spring.autoconfigure.exclude=",
                "eduops.messaging.ticket-events.enabled=true",
                "eduops.messaging.ticket-events.exchange=eduops.test.ticket.events.dlq",
                "eduops.messaging.ticket-events.queue=eduops.test.ticket.status-events.dlq",
                "eduops.messaging.ticket-events.routing-key=test.ticket.status.changed.v1",
                "eduops.messaging.ticket-events.dead-letter-exchange=eduops.test.ticket.events.dlq.dead",
                "eduops.messaging.ticket-events.dead-letter-queue=eduops.test.ticket.status-events.dlq.dead",
                "eduops.messaging.ticket-events.dead-letter-routing-key=test.ticket.status.changed.dlq.v1",
                "eduops.outbox.delivery.enabled=false",
                "eduops.outbox.inbox.enabled=true"
        }
)
@ActiveProfiles("local")
@EnabledIfSystemProperty(
        named = "runRabbitMqDeadLetterIntegrationTests",
        matches = "true"
)
class TicketEventInboxDeadLetterRabbitMqIntegrationTest {

    private static final String EXCHANGE = "eduops.test.ticket.events.dlq";
    private static final String ROUTING_KEY = "test.ticket.status.changed.v1";
    private static final String MAIN_QUEUE = "eduops.test.ticket.status-events.dlq";
    private static final String DEAD_LETTER_QUEUE = "eduops.test.ticket.status-events.dlq.dead";
    private static final String DEAD_LETTER_EXCHANGE = "eduops.test.ticket.events.dlq.dead";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private AmqpAdmin amqpAdmin;

    @AfterEach
    void cleanUpDedicatedTestTopology() {
        amqpAdmin.deleteQueue(MAIN_QUEUE);
        amqpAdmin.deleteQueue(DEAD_LETTER_QUEUE);
        amqpAdmin.deleteExchange(EXCHANGE);
        amqpAdmin.deleteExchange(DEAD_LETTER_EXCHANGE);
    }

    @Test
    void moves_a_malformed_message_to_the_dead_letter_queue_without_requeueing()
            throws InterruptedException {
        String malformedBody = "malformed-ticket-event-" + UUID.randomUUID();
        rabbitTemplate.convertAndSend(EXCHANGE, ROUTING_KEY, malformedBody);

        Message deadLettered = awaitDeadLetteredMessage();

        assertThat(new String(deadLettered.getBody(), StandardCharsets.UTF_8))
                .isEqualTo(malformedBody);
    }

    private Message awaitDeadLetteredMessage() throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(10));
        while (Instant.now().isBefore(deadline)) {
            Message message = rabbitTemplate.receive(DEAD_LETTER_QUEUE, 250);
            if (message != null) {
                return message;
            }
            Thread.sleep(100);
        }
        fail("malformed message did not arrive in the dedicated dead-letter queue");
        return null;
    }
}
