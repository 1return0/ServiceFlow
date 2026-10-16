package com.serviceflow.business.ticket.manager.mq.outbox;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.ReturnedMessage;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;

class RabbitMqTicketOutboxEventPublisherTest {

    @Test
    void publishes_payload_with_stable_event_metadata_headers() {
        RabbitTemplate rabbitTemplate = mock(RabbitTemplate.class);
        TicketOutboxEventEntity event = new TicketOutboxEventEntity();
        event.setId(UUID.fromString("009e3cce-8f4d-448d-a060-6ce2624eac77"));
        event.setAggregateType("ticket");
        event.setAggregateId(UUID.fromString("31f62da3-b6b0-4a10-9a75-22b558d5ac34"));
        event.setEventType("ticket.status_changed.v1");
        event.setCreatedAt(Instant.parse("2026-09-16T08:00:00Z"));
        event.setPayload("{\"status\":\"IN_PROGRESS\"}");
        RabbitMqTicketOutboxEventPublisher publisher =
                new RabbitMqTicketOutboxEventPublisher(
                        rabbitTemplate,
                        "eduops.ticket.events",
                        "ticket.status.changed.v1",
                        Duration.ofSeconds(1)
                );

        doAnswer(invocation -> {
            CorrelationData correlationData = invocation.getArgument(4);
            correlationData.getFuture().complete(new CorrelationData.Confirm(true, null));
            return null;
        }).when(rabbitTemplate).convertAndSend(
                any(String.class),
                any(String.class),
                any(),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );

        publisher.publish(event);

        ArgumentCaptor<MessagePostProcessor> processorCaptor =
                ArgumentCaptor.forClass(MessagePostProcessor.class);
        ArgumentCaptor<CorrelationData> correlationCaptor = ArgumentCaptor.forClass(
                CorrelationData.class
        );
        verify(rabbitTemplate).convertAndSend(
                eq("eduops.ticket.events"),
                eq("ticket.status.changed.v1"),
                eq("{\"status\":\"IN_PROGRESS\"}"),
                processorCaptor.capture(),
                correlationCaptor.capture()
        );
        Message message = processorCaptor.getValue().postProcessMessage(
                new Message(new byte[0], new MessageProperties())
        );
        MessageProperties properties = message.getMessageProperties();
        assertThat(properties.getContentType()).isEqualTo(MessageProperties.CONTENT_TYPE_JSON);
        assertThat(properties.getHeaders()).containsEntry("eventId", event.getId().toString());
        assertThat(properties.getHeaders()).containsEntry("eventType", event.getEventType());
        assertThat(properties.getHeaders()).containsEntry("aggregateType", "ticket");
        assertThat(properties.getHeaders()).containsEntry(
                "aggregateId",
                event.getAggregateId().toString()
        );
        assertThat(correlationCaptor.getValue().getId()).isEqualTo(event.getId().toString());
    }

    @Test
    void rejects_an_acknowledged_message_that_the_broker_could_not_route() {
        RabbitTemplate rabbitTemplate = mock(RabbitTemplate.class);
        TicketOutboxEventEntity event = new TicketOutboxEventEntity();
        event.setId(UUID.fromString("009e3cce-8f4d-448d-a060-6ce2624eac77"));
        event.setAggregateType("ticket");
        event.setAggregateId(UUID.fromString("31f62da3-b6b0-4a10-9a75-22b558d5ac34"));
        event.setEventType("ticket.status_changed.v1");
        event.setCreatedAt(Instant.parse("2026-09-16T08:00:00Z"));
        event.setPayload("{\"status\":\"IN_PROGRESS\"}");
        RabbitMqTicketOutboxEventPublisher publisher =
                new RabbitMqTicketOutboxEventPublisher(
                        rabbitTemplate,
                        "eduops.ticket.events",
                        "ticket.missing.route.v1",
                        Duration.ofSeconds(1)
                );

        doAnswer(invocation -> {
            CorrelationData correlationData = invocation.getArgument(4);
            correlationData.setReturned(new ReturnedMessage(
                    new Message(new byte[0], new MessageProperties()),
                    312,
                    "NO_ROUTE",
                    "eduops.ticket.events",
                    "ticket.missing.route.v1"
            ));
            correlationData.getFuture().complete(new CorrelationData.Confirm(true, null));
            return null;
        }).when(rabbitTemplate).convertAndSend(
                any(String.class),
                any(String.class),
                any(),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );

        assertThatThrownBy(() -> publisher.publish(event))
                .isInstanceOf(OutboxPublishConfirmationException.class)
                .hasMessageContaining("could not route event")
                .hasMessageContaining("replyCode=312");
    }
}
