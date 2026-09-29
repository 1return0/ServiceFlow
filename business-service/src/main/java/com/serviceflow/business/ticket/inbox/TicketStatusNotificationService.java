package com.serviceflow.business.ticket.inbox;

import java.time.Instant;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.serviceflow.business.ticket.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.event.TicketStatusChangedEventPayload;
import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import lombok.RequiredArgsConstructor;

/** Creates the durable student-facing effect of a consumed ticket status event. */
@Service
@RequiredArgsConstructor
public class TicketStatusNotificationService {

    private static final String STATUS_CHANGED_EVENT = "ticket.status_changed.v1";
    private static final String CLAIMED_EVENT = "ticket.claimed.v1";

    private final TicketNotificationMapper notificationMapper;
    private final ObjectMapper objectMapper;

    public void createForStatusChange(TicketEventInboxMessage event) {
        if (!(STATUS_CHANGED_EVENT.equals(event.eventType()) || CLAIMED_EVENT.equals(event.eventType()))
                || !"ticket".equals(event.aggregateType())) {
            throw new IllegalArgumentException("unsupported ticket notification event");
        }

        TicketStatusChangedEventPayload payload = readPayload(event.payload());
        if (!event.aggregateId().equals(payload.ticketId())) {
            throw new IllegalArgumentException(
                    "ticket status event aggregate id does not match payload ticket id"
            );
        }

        int insertedRows = notificationMapper.insert(new TicketNotificationEntity(
                UUID.randomUUID(),
                event.eventId(),
                payload.requesterReference(),
                payload.ticketId(),
                event.eventType(),
                CLAIMED_EVENT.equals(event.eventType())
                        ? "Your service ticket has been claimed by support."
                        : "Your service ticket status is now " + payload.status().name() + ".",
                Instant.now(),
                null
        ));
        if (insertedRows != 1) {
            throw new IllegalStateException(
                    "ticket notification insert did not affect exactly one row"
            );
        }
    }

    private TicketStatusChangedEventPayload readPayload(String rawPayload) {
        try {
            return objectMapper.readValue(
                    rawPayload,
                    TicketStatusChangedEventPayload.class
            );
        } catch (JsonProcessingException | IllegalArgumentException error) {
            throw new IllegalArgumentException(
                    "ticket status event payload is invalid",
                    error
            );
        }
    }
}
