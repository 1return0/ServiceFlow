package com.serviceflow.business.ticket.config;

import java.util.Map;

import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.rabbit.config.RetryInterceptorBuilder;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.retry.RejectAndDontRequeueRecoverer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.policy.SimpleRetryPolicy;

/**
 * Reliability policy owned by the ticket-event Consumer, instead of relying on
 * broad application defaults that may unintentionally affect other listeners.
 */
@Configuration
@ConditionalOnProperty(
        prefix = "eduops.outbox.inbox",
        name = "enabled",
        havingValue = "true"
)
public class TicketEventConsumerReliabilityConfiguration {

    @Bean
    SimpleRabbitListenerContainerFactory ticketEventRabbitListenerContainerFactory(
            ConnectionFactory connectionFactory,
            @Value("${eduops.messaging.ticket-events.consumer.retry.max-attempts:3}") int maxAttempts,
            @Value("${eduops.messaging.ticket-events.consumer.retry.initial-interval-millis:1000}")
            long initialIntervalMillis,
            @Value("${eduops.messaging.ticket-events.consumer.retry.multiplier:2.0}") double multiplier,
            @Value("${eduops.messaging.ticket-events.consumer.retry.max-interval-millis:5000}")
            long maxIntervalMillis
    ) {
        SimpleRabbitListenerContainerFactory factory =
                new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setDefaultRequeueRejected(false);
        factory.setAdviceChain(RetryInterceptorBuilder.stateless()
                .retryPolicy(new SimpleRetryPolicy(
                        maxAttempts,
                        Map.of(AmqpRejectAndDontRequeueException.class, false),
                        true,
                        true
                ))
                .backOffOptions(initialIntervalMillis, multiplier, maxIntervalMillis)
                .recoverer(new RejectAndDontRequeueRecoverer())
                .build());
        return factory;
    }
}
