package com.serviceflow.business.ticket.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * A consumer-owned RabbitMQ topology. It can be declared without enabling the
 * Outbox scheduler, which keeps consumer smoke tests isolated from pending events.
 */
@Configuration
@ConditionalOnProperty(
        prefix = "eduops.messaging.ticket-events",
        name = "enabled",
        havingValue = "true"
)
public class TicketEventRabbitMqTopologyConfiguration {

    @Bean
    TopicExchange ticketOutboxExchange(
            @Value("${eduops.messaging.ticket-events.exchange:eduops.ticket.events}") String exchangeName
    ) {
        return new TopicExchange(exchangeName, true, false);
    }

    @Bean
    TopicExchange ticketOutboxDeadLetterExchange(
            @Value("${eduops.messaging.ticket-events.dead-letter-exchange:eduops.ticket.events.dlx}")
            String deadLetterExchangeName
    ) {
        return new TopicExchange(deadLetterExchangeName, true, false);
    }

    @Bean
    Queue ticketStatusChangedQueue(
            @Value("${eduops.messaging.ticket-events.queue:eduops.ticket.status-events.v1}") String queueName,
            @Value("${eduops.messaging.ticket-events.dead-letter-exchange:eduops.ticket.events.dlx}")
            String deadLetterExchangeName,
            @Value("${eduops.messaging.ticket-events.dead-letter-routing-key:ticket.status.changed.dlq.v1}")
            String deadLetterRoutingKey
    ) {
        return QueueBuilder.durable(queueName)
                .deadLetterExchange(deadLetterExchangeName)
                .deadLetterRoutingKey(deadLetterRoutingKey)
                .build();
    }

    @Bean
    Queue ticketStatusChangedDeadLetterQueue(
            @Value("${eduops.messaging.ticket-events.dead-letter-queue:eduops.ticket.status-events.dlq.v1}")
            String deadLetterQueueName
    ) {
        return QueueBuilder.durable(deadLetterQueueName).build();
    }

    @Bean
    Binding ticketStatusChangedBinding(
            Queue ticketStatusChangedQueue,
            TopicExchange ticketOutboxExchange,
            @Value("${eduops.messaging.ticket-events.routing-key:ticket.status.changed.v1}") String routingKey
    ) {
        return BindingBuilder.bind(ticketStatusChangedQueue)
                .to(ticketOutboxExchange)
                .with(routingKey);
    }

    @Bean
    Binding ticketStatusChangedDeadLetterBinding(
            Queue ticketStatusChangedDeadLetterQueue,
            TopicExchange ticketOutboxDeadLetterExchange,
            @Value("${eduops.messaging.ticket-events.dead-letter-routing-key:ticket.status.changed.dlq.v1}")
            String deadLetterRoutingKey
    ) {
        return BindingBuilder.bind(ticketStatusChangedDeadLetterQueue)
                .to(ticketOutboxDeadLetterExchange)
                .with(deadLetterRoutingKey);
    }
}
