package com.serviceflow.business.ticket.service;

import org.springframework.stereotype.Component;

import com.serviceflow.business.ticket.enums.TicketStatus;

/**
 * Authoritative state-transition policy for a ticket. The Agent may recommend an action,
 * but this Java policy decides whether the requested transition is legal.
 */
@Component
public class TicketStatusTransitionPolicy {

    public boolean isAllowed(TicketStatus from, TicketStatus to) {
        return switch (from) {
            case OPEN -> to == TicketStatus.IN_PROGRESS || to == TicketStatus.ESCALATED;
            case IN_PROGRESS -> to == TicketStatus.WAITING_FOR_REQUESTER
                    || to == TicketStatus.RESOLVED
                    || to == TicketStatus.ESCALATED;
            case WAITING_FOR_REQUESTER -> to == TicketStatus.IN_PROGRESS
                    || to == TicketStatus.CLOSED
                    || to == TicketStatus.ESCALATED;
            case RESOLVED -> to == TicketStatus.CLOSED || to == TicketStatus.IN_PROGRESS;
            case ESCALATED -> to == TicketStatus.IN_PROGRESS || to == TicketStatus.CLOSED;
            case CLOSED -> false;
        };
    }
}
