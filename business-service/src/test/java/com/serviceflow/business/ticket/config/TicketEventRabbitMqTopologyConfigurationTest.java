package com.serviceflow.business.ticket.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;

class TicketEventRabbitMqTopologyConfigurationTest {

    @Test
    void declares_a_durable_dead_letter_path_for_exhausted_consumer_failures() {
        TicketEventRabbitMqTopologyConfiguration configuration =
                new TicketEventRabbitMqTopologyConfiguration();

        Queue mainQueue = configuration.ticketStatusChangedQueue(
                "eduops.ticket.status-events.v1",
                "eduops.ticket.events.dlx",
                "ticket.status.changed.dlq.v1"
        );
        TopicExchange deadLetterExchange = configuration.ticketOutboxDeadLetterExchange(
                "eduops.ticket.events.dlx"
        );
        Queue deadLetterQueue = configuration.ticketStatusChangedDeadLetterQueue(
                "eduops.ticket.status-events.dlq.v1"
        );
        Binding deadLetterBinding = configuration.ticketStatusChangedDeadLetterBinding(
                deadLetterQueue,
                deadLetterExchange,
                "ticket.status.changed.dlq.v1"
        );

        assertThat(mainQueue.isDurable()).isTrue();
        assertThat(mainQueue.getArguments()).containsEntry(
                "x-dead-letter-exchange",
                "eduops.ticket.events.dlx"
        );
        assertThat(mainQueue.getArguments()).containsEntry(
                "x-dead-letter-routing-key",
                "ticket.status.changed.dlq.v1"
        );
        assertThat(deadLetterQueue.isDurable()).isTrue();
        assertThat(deadLetterBinding.getExchange()).isEqualTo("eduops.ticket.events.dlx");
        assertThat(deadLetterBinding.getRoutingKey()).isEqualTo("ticket.status.changed.dlq.v1");
    }
}
