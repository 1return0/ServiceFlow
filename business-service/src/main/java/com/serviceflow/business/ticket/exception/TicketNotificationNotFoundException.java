package com.serviceflow.business.ticket.exception;

import java.util.UUID;

/** Uses the same 404 result for a missing notification and one owned by another student. */
public class TicketNotificationNotFoundException extends RuntimeException {

    public TicketNotificationNotFoundException(UUID notificationId) {
        super("notification not found: " + notificationId);
    }
}
