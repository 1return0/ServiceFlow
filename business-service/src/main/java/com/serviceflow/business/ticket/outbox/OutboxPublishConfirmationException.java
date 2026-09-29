package com.serviceflow.business.ticket.outbox;

/** RabbitMQ did not positively confirm the specific Outbox event in time. */
public class OutboxPublishConfirmationException extends RuntimeException {

    public OutboxPublishConfirmationException(String message) {
        super(message);
    }

    public OutboxPublishConfirmationException(String message, Throwable cause) {
        super(message, cause);
    }
}
