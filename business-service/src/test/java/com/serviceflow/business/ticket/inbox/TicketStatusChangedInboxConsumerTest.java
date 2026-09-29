package com.serviceflow.business.ticket.inbox;

import static org.mockito.Mockito.verify;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;

class TicketStatusChangedInboxConsumerTest {

    private final TicketStatusChangedEventProcessingService processingService = Mockito.mock(
            TicketStatusChangedEventProcessingService.class
    );
    private final TicketStatusChangedInboxConsumer consumer =
            new TicketStatusChangedInboxConsumer(processingService);

    @Test
    void converts_rabbit_headers_and_body_into_the_inbox_contract() {
        UUID eventId = UUID.fromString("11111111-1111-1111-1111-111111111111");
        UUID aggregateId = UUID.fromString("22222222-2222-2222-2222-222222222222");
        Message message = MessageBuilder.withBody(
                        "{\"status\":\"RESOLVED\"}".getBytes(StandardCharsets.UTF_8)
                )
                .setHeader("eventId", eventId.toString())
                .setHeader("eventType", "ticket.status_changed.v1")
                .setHeader("aggregateType", "ticket")
                .setHeader("aggregateId", aggregateId.toString())
                .build();

        consumer.consume(message);

        verify(processingService).process(new TicketEventInboxMessage(
                eventId,
                "ticket.status_changed.v1",
                "ticket",
                aggregateId,
                "{\"status\":\"RESOLVED\"}"
        ));
    }
}
