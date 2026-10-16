package com.serviceflow.business.ticket.exception;

import com.serviceflow.business.ticket.domain.OperatorRole;

public class TicketAuthorizationException extends RuntimeException {

    public TicketAuthorizationException(OperatorRole role) {
        super("role is not allowed to update ticket status: " + role);
    }
}
