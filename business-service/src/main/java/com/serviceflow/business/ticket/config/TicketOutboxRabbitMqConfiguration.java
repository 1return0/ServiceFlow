package com.serviceflow.business.ticket.config;

import java.time.Duration;

import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.serviceflow.business.ticket.outbox.RabbitMqTicketOutboxEventPublisher;
import com.serviceflow.business.ticket.outbox.TicketOutboxEventPublisher;

/** Creates the Outbox publisher; topology is owned by TicketEventRabbitMqTopologyConfiguration. */
@Configuration
@ConditionalOnProperty(
        prefix = "eduops.outbox.delivery",
        name = "enabled",
        havingValue = "true"
)
public class TicketOutboxRabbitMqConfiguration {

    /**
     * Enables mandatory-message return handling. Spring also associates a returned
     * message with the matching CorrelationData used by the publisher.
     */
    @Bean
    RabbitTemplate.ReturnsCallback ticketOutboxReturnsCallback() {
        return returned -> {
            // RabbitTemplate stores this ReturnedMessage on the matching
            // CorrelationData before invoking this callback. The publisher then
            // turns it into a retryable Outbox delivery failure.
        };
    }

    @Bean
    TicketOutboxEventPublisher ticketOutboxEventPublisher(
            RabbitTemplate rabbitTemplate,
            RabbitTemplate.ReturnsCallback ticketOutboxReturnsCallback,
            @Value("${eduops.messaging.ticket-events.exchange:eduops.ticket.events}") String exchange,
            @Value("${eduops.messaging.ticket-events.routing-key:ticket.status.changed.v1}") String routingKey,
            @Value("${eduops.outbox.delivery.confirm-timeout-millis:3000}") long confirmTimeoutMillis
    ) {
        rabbitTemplate.setReturnsCallback(ticketOutboxReturnsCallback);
        return new RabbitMqTicketOutboxEventPublisher(
                rabbitTemplate,
                exchange,
                routingKey,
                Duration.ofMillis(confirmTimeoutMillis)
        );
    }
}
