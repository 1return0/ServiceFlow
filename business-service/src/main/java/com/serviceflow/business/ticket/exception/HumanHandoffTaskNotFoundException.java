package com.serviceflow.business.ticket.exception;

import java.util.UUID;

public class HumanHandoffTaskNotFoundException extends RuntimeException {
    public HumanHandoffTaskNotFoundException(UUID taskId) {
        super("human handoff task was not found: " + taskId);
    }
}
