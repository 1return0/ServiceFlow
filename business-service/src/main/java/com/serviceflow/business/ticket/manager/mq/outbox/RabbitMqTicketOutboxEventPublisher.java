package com.serviceflow.business.ticket.manager.mq.outbox;

import java.time.Duration;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.ReturnedMessage;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import lombok.RequiredArgsConstructor;

import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;

/** Publishes the immutable Outbox payload and stable idempotency metadata. */
@RequiredArgsConstructor
public class RabbitMqTicketOutboxEventPublisher implements TicketOutboxEventPublisher {

    private final RabbitTemplate rabbitTemplate;
    private final String exchange;
    private final String routingKey;
    private final Duration confirmTimeout;

    @Override
    public void publish(TicketOutboxEventEntity event) {
        CorrelationData correlationData = new CorrelationData(event.getId().toString());
        rabbitTemplate.convertAndSend(
                exchange,
                routingKey,
                event.getPayload(),
                message -> {
                    MessageProperties properties = message.getMessageProperties();
                    properties.setContentType(MessageProperties.CONTENT_TYPE_JSON);
                    properties.setHeader("eventId", event.getId().toString());
                    properties.setHeader("eventType", event.getEventType());
                    properties.setHeader("aggregateType", event.getAggregateType());
                    properties.setHeader("aggregateId", event.getAggregateId().toString());
                    properties.setHeader("occurredAt", event.getCreatedAt().toString());
                    return message;
                },
                correlationData
        );
        awaitBrokerConfirmation(event.getId().toString(), correlationData);
    }

    private void awaitBrokerConfirmation(
            String eventId,
            CorrelationData correlationData
    ) {
        try {
            CorrelationData.Confirm confirm = correlationData.getFuture().get(
                    confirmTimeout.toMillis(),
                    TimeUnit.MILLISECONDS
            );
            if (!confirm.isAck()) {
                throw new OutboxPublishConfirmationException(
                        "rabbitmq broker negatively acknowledged event: " + eventId
                );
            }
            ReturnedMessage returned = correlationData.getReturned();
            if (returned != null) {
                throw new OutboxPublishConfirmationException(
                        "rabbitmq broker could not route event: "
                                + eventId
                                + ", replyCode="
                                + returned.getReplyCode()
                                + ", routingKey="
                                + returned.getRoutingKey()
                );
            }
        } catch (TimeoutException error) {
            throw new OutboxPublishConfirmationException(
                    "rabbitmq broker confirmation timed out for event: " + eventId,
                    error
            );
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new OutboxPublishConfirmationException(
                    "rabbitmq broker confirmation was interrupted for event: " + eventId,
                    error
            );
        } catch (ExecutionException error) {
            throw new OutboxPublishConfirmationException(
                    "rabbitmq broker confirmation failed for event: " + eventId,
                    error
            );
        }
    }
}
