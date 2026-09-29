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
}
