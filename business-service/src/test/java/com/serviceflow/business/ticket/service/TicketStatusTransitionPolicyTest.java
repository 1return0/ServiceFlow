package com.serviceflow.business.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

import com.serviceflow.business.ticket.enums.TicketStatus;

class TicketStatusTransitionPolicyTest {

    private final TicketStatusTransitionPolicy policy = new TicketStatusTransitionPolicy();

    @Test
    void allows_an_open_ticket_to_start_processing() {
        assertThat(policy.isAllowed(TicketStatus.OPEN, TicketStatus.IN_PROGRESS)).isTrue();
    }

    @Test
    void rejects_reopening_a_closed_ticket_in_the_first_policy_version() {
        assertThat(policy.isAllowed(TicketStatus.CLOSED, TicketStatus.IN_PROGRESS)).isFalse();
    }

    @Test
    void rejects_skipping_directly_from_open_to_closed() {
        assertThat(policy.isAllowed(TicketStatus.OPEN, TicketStatus.CLOSED)).isFalse();
    }

    @Test
    void supports_resolving_closing_and_reworking_the_active_workflow() {
        assertThat(policy.isAllowed(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED)).isTrue();
        assertThat(policy.isAllowed(TicketStatus.RESOLVED, TicketStatus.CLOSED)).isTrue();
        assertThat(policy.isAllowed(TicketStatus.RESOLVED, TicketStatus.IN_PROGRESS)).isTrue();
        assertThat(policy.isAllowed(TicketStatus.OPEN, TicketStatus.RESOLVED)).isFalse();
        assertThat(policy.isAllowed(TicketStatus.IN_PROGRESS, TicketStatus.CLOSED)).isFalse();
    }

    @Test
    @SuppressWarnings("deprecation")
    void retired_statuses_cannot_be_entered_or_transitioned() {
        for (TicketStatus status : TicketStatus.values()) {
            assertThat(policy.isAllowed(status, TicketStatus.WAITING_FOR_REQUESTER)).isFalse();
            assertThat(policy.isAllowed(status, TicketStatus.ESCALATED)).isFalse();
            assertThat(policy.isAllowed(TicketStatus.WAITING_FOR_REQUESTER, status)).isFalse();
            assertThat(policy.isAllowed(TicketStatus.ESCALATED, status)).isFalse();
        }
    }
}
