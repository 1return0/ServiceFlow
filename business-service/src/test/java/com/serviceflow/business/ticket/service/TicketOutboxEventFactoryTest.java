package com.serviceflow.business.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.serviceflow.business.ticket.entity.TicketEntity;
import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import com.serviceflow.business.ticket.enums.TicketStatus;

class TicketOutboxEventFactoryTest {

    private final TicketOutboxEventFactory factory = new TicketOutboxEventFactory(
            new ObjectMapper()
    );

    @Test
    void creates_an_unpublished_status_changed_event_for_the_updated_ticket() {
        UUID ticketId = UUID.fromString("009e3cce-8f4d-448d-a060-6ce2624eac77");
        TicketEntity ticket = new TicketEntity(
                ticketId,
                "student-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "network issue",
                Instant.parse("2026-09-15T08:00:00Z"),
                TicketStatus.IN_PROGRESS,
                1L
        );

        var event = factory.statusChanged(ticket);

        assertThat(event.getAggregateType()).isEqualTo("ticket");
        assertThat(event.getAggregateId()).isEqualTo(ticketId);
        assertThat(event.getEventType()).isEqualTo("ticket.status_changed.v1");
        assertThat(event.getPayload()).contains("\"status\":\"IN_PROGRESS\"");
        assertThat(event.getPayload()).contains("\"requesterReference\":\"student-001\"");
        assertThat(event.getPublishedAt()).isNull();
        assertThat(event.getPublishAttempts()).isZero();
    }
}
