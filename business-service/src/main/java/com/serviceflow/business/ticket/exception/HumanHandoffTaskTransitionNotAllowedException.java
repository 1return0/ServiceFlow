package com.serviceflow.business.ticket.exception;

import java.util.UUID;

public class HumanHandoffTaskTransitionNotAllowedException extends RuntimeException {
    public HumanHandoffTaskTransitionNotAllowedException(UUID taskId) {
        super("human handoff task transition is not allowed: " + taskId);
    }
}
