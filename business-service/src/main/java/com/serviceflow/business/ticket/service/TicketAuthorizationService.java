package com.serviceflow.business.ticket.service;

import org.springframework.stereotype.Component;

import com.serviceflow.business.ticket.enums.OperatorRole;

/** Minimal RBAC policy for the synthetic EduOps service. */
@Component
public class TicketAuthorizationService {

    public boolean canUpdateStatus(OperatorRole role) {
        return role == OperatorRole.SUPPORT_AGENT || role == OperatorRole.ADMIN;
    }

    /**
     * A student may only read the ticket they created. Support and admin roles
     * need cross-student visibility to perform their operational duties.
     */
    public boolean canReadTicket(
            OperatorRole role,
            String actorReference,
            String requesterReference
    ) {
        if (role == OperatorRole.SUPPORT_AGENT || role == OperatorRole.ADMIN) {
            return true;
        }
        return role == OperatorRole.STUDENT
                && actorReference != null
                && actorReference.equals(requesterReference);
    }
}
