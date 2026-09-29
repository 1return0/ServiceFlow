package com.serviceflow.business.ticket.enums;

/** The allowed values of a ticket's current state. Transition rules come later. */
public enum TicketStatus {
    OPEN,
    IN_PROGRESS,
    WAITING_FOR_REQUESTER,
    RESOLVED,
    CLOSED,
    ESCALATED
}
