package com.serviceflow.business.ticket.service;

import java.time.Instant;
import java.util.UUID;

import org.springframework.stereotype.Component;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.serviceflow.business.ticket.dao.entity.TicketEntity;
import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.manager.mq.event.TicketStatusChangedEventPayload;

/** Creates append-only integration events; publishing is deliberately a later concern. */
@Component
public class TicketOutboxEventFactory {

    private final ObjectMapper objectMapper;

    public TicketOutboxEventFactory(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public TicketOutboxEventEntity statusChanged(TicketEntity ticket) {
        return event(ticket, "ticket.status_changed.v1");
    }

    public TicketOutboxEventEntity claimed(TicketEntity ticket) {
        return event(ticket, "ticket.claimed.v1");
    }

    private TicketOutboxEventEntity event(TicketEntity ticket, String eventType) {
        return new TicketOutboxEventEntity(
                UUID.randomUUID(),
                "ticket",
                ticket.getId(),
                eventType,
                writePayload(ticket),
                Instant.now(),
                null,
                0,
                null,
                null,
                null
        );
    }

    private String writePayload(TicketEntity ticket) {
        try {
            return objectMapper.writeValueAsString(new TicketStatusChangedEventPayload(
                    ticket.getId(),
                    ticket.getRequesterReference(),
                    ticket.getStatus(),
                    ticket.getVersion() == null ? 0L : ticket.getVersion()
            ));
        } catch (JsonProcessingException error) {
            throw new IllegalStateException("ticket status event payload could not be serialized", error);
        }
    }
}
