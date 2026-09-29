package com.serviceflow.business.ticket.exception;

import com.serviceflow.business.ticket.enums.TicketStatus;

public class TicketStatusTransitionNotAllowedException extends RuntimeException {

    public TicketStatusTransitionNotAllowedException(TicketStatus from, TicketStatus to) {
        super("ticket status transition is not allowed: " + from + " -> " + to);
    }
}
