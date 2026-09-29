package com.serviceflow.business.ticket.exception;

import java.util.UUID;

public class TicketUpdateConflictException extends RuntimeException {

    public TicketUpdateConflictException(UUID ticketId) {
        super("ticket was changed by another request: " + ticketId);
    }
}
