package com.serviceflow.business.ticket.enums;

/** Four active workflow states; retired values are read-only compatibility for historical data. */
public enum TicketStatus {
    OPEN,
    IN_PROGRESS,
    RESOLVED,
    CLOSED,
    /** Compatibility only: no active waiting-for-requester workflow. */
    @Deprecated
    WAITING_FOR_REQUESTER,
    /** Compatibility only: human handoff tasks are separate from ticket escalation. */
    @Deprecated
    ESCALATED
}
