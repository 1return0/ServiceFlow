package com.serviceflow.business.ticket.manager.mq.outbox;

import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;

/** Infrastructure boundary. A RabbitMQ implementation is added in Week 7. */
@FunctionalInterface
public interface TicketOutboxEventPublisher {

    void publish(TicketOutboxEventEntity event);
}
