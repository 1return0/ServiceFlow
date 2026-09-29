package com.serviceflow.business.ticket.outbox;

import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;

/** Infrastructure boundary. A RabbitMQ implementation is added in Week 7. */
@FunctionalInterface
public interface TicketOutboxEventPublisher {

    void publish(TicketOutboxEventEntity event);
}
