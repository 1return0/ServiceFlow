package com.serviceflow.business.ticket.exception;

import java.util.UUID;

public class TicketNotFoundException extends RuntimeException {

    public TicketNotFoundException(UUID ticketId) {
        super("ticket not found: " + ticketId);
    }
}
