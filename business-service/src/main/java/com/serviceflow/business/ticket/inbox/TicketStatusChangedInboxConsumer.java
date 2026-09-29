package com.serviceflow.business.ticket.inbox;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;

import org.springframework.amqp.core.Message;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;

/** Receives ticket events and delegates the durable business effect to one transaction. */
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(
        prefix = "eduops.outbox.inbox",
        name = "enabled",
        havingValue = "true"
)
public class TicketStatusChangedInboxConsumer {

    private final TicketStatusChangedEventProcessingService processingService;

    @RabbitListener(
            queues = "${eduops.messaging.ticket-events.queue:eduops.ticket.status-events.v1}",
            containerFactory = "ticketEventRabbitListenerContainerFactory"
    )
    public void consume(Message message) {
        try {
            Map<String, Object> headers = message.getMessageProperties().getHeaders();
            processingService.process(new TicketEventInboxMessage(
                    requiredUuidHeader(headers, "eventId"),
                    requiredStringHeader(headers, "eventType"),
                    requiredStringHeader(headers, "aggregateType"),
                    requiredUuidHeader(headers, "aggregateId"),
                    new String(message.getBody(), StandardCharsets.UTF_8)
            ));
        } catch (IllegalArgumentException error) {
            // A malformed event will never become valid through retrying. Reject it
            // once so the queue's configured dead-letter path can isolate it.
            throw new AmqpRejectAndDontRequeueException(
                    "ticket event violates the consumer contract",
                    error
            );
        }
    }

    private static UUID requiredUuidHeader(
            Map<String, Object> headers,
            String headerName
    ) {
        try {
            return UUID.fromString(requiredStringHeader(headers, headerName));
        } catch (IllegalArgumentException error) {
            throw new IllegalArgumentException(
                    "message header must be a UUID: " + headerName,
                    error
            );
        }
    }

    private static String requiredStringHeader(
            Map<String, Object> headers,
            String headerName
    ) {
        Object value = headers.get(headerName);
        if (value == null || value.toString().isBlank()) {
            throw new IllegalArgumentException(
                    "required message header is missing: " + headerName
            );
        }
        return value.toString();
    }
}
