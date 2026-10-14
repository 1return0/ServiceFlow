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
            case OPEN -> to == TicketStatus.IN_PROGRESS;
            case IN_PROGRESS -> to == TicketStatus.RESOLVED;
            case RESOLVED -> to == TicketStatus.CLOSED || to == TicketStatus.IN_PROGRESS;
            case CLOSED -> false;
            // Retired enum values remain readable for historical rows, but cannot transition.
            default -> false;
        };
    }
}
