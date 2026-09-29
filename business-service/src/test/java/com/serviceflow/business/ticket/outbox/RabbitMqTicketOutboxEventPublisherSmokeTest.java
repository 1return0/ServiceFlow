package com.serviceflow.business.ticket.outbox;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.autoconfigure.flyway.FlywayAutoConfiguration;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestConstructor;

import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;

/**
 * Optional VM-only AMQP smoke. It declares an isolated, exclusive and
 * auto-delete topology, then removes it in finally.
 */
@ActiveProfiles("local")
@TestConstructor(autowireMode = TestConstructor.AutowireMode.ALL)
@SpringBootTest(
        classes = RabbitMqTicketOutboxEventPublisherSmokeTest.RabbitMqSmokeApplication.class,
        properties = {
                "spring.main.web-application-type=none",
                "spring.rabbitmq.publisher-confirm-type=correlated",
                "spring.rabbitmq.template.mandatory=true"
        }
)
@EnabledIfSystemProperty(
        named = "runRabbitMqSmokeTests",
        matches = "true"
)
class RabbitMqTicketOutboxEventPublisherSmokeTest {

    private final RabbitTemplate rabbitTemplate;
    private final RabbitAdmin rabbitAdmin;

    RabbitMqTicketOutboxEventPublisherSmokeTest(
            RabbitTemplate rabbitTemplate,
            ConnectionFactory connectionFactory
    ) {
        this.rabbitTemplate = rabbitTemplate;
        this.rabbitAdmin = new RabbitAdmin(connectionFactory);
    }

    @Test
    void publishes_to_an_isolated_vm_queue_with_idempotency_headers() {
        String suffix = UUID.randomUUID().toString();
        String exchangeName = "eduops.smoke.ticket.events." + suffix;
        String queueName = "eduops.smoke.ticket.status." + suffix;
        String routingKey = "ticket.status.changed.v1";
        TopicExchange exchange = new TopicExchange(exchangeName, false, true);
        Queue queue = new Queue(queueName, false, true, true);
        rabbitAdmin.declareExchange(exchange);
        rabbitAdmin.declareQueue(queue);
        rabbitAdmin.declareBinding(
                BindingBuilder.bind(queue).to(exchange).with(routingKey)
        );

        TicketOutboxEventEntity event = new TicketOutboxEventEntity();
        event.setId(UUID.randomUUID());
        event.setAggregateType("ticket");
        event.setAggregateId(UUID.randomUUID());
        event.setEventType("ticket.status_changed.v1");
        event.setCreatedAt(Instant.parse("2026-09-17T08:00:00Z"));
        event.setPayload("{\"status\":\"IN_PROGRESS\"}");

        try {
            new RabbitMqTicketOutboxEventPublisher(
                    rabbitTemplate,
                    exchangeName,
                    routingKey,
                    Duration.ofSeconds(3)
            ).publish(event);

            Message received = rabbitTemplate.receive(queueName, 5_000);
            assertThat(received).isNotNull();
            assertThat(new String(received.getBody(), StandardCharsets.UTF_8))
                    .isEqualTo(event.getPayload());
            assertThat(received.getMessageProperties().getHeaders())
                    .containsEntry("eventId", event.getId().toString())
                    .containsEntry("eventType", event.getEventType());
        } finally {
            rabbitAdmin.deleteQueue(queueName);
            rabbitAdmin.deleteExchange(exchangeName);
        }
    }

    @SpringBootConfiguration
    @EnableAutoConfiguration(exclude = {
            DataSourceAutoConfiguration.class,
            FlywayAutoConfiguration.class
    })
    static class RabbitMqSmokeApplication {
    }
}
