package com.serviceflow.business.ticket.manager.mq.outbox;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.Test;

import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;

class TicketOutboxDeliveryServiceTest {

    @Test
    void claims_publishes_and_acknowledges_an_event_with_the_same_lease() {
        TicketOutboxEventMapper mapper = mock(TicketOutboxEventMapper.class);
        TicketOutboxEventPublisher publisher = mock(TicketOutboxEventPublisher.class);
        TicketOutboxEventEntity event = new TicketOutboxEventEntity();
        event.setId(UUID.fromString("009e3cce-8f4d-448d-a060-6ce2624eac77"));
        when(mapper.claimNextUnpublished(anyInt(), any(), any(), any()))
                .thenReturn(List.of(event));
        when(mapper.markPublished(eq(event.getId()), any(), any())).thenReturn(1);

        int published = new TicketOutboxDeliveryService(
                mapper,
                publisher,
                Clock.fixed(Instant.parse("2026-09-15T08:00:00Z"), ZoneOffset.UTC)
        ).deliverNextBatch(10);

        assertThat(published).isEqualTo(1);
        verify(publisher).publish(event);
        verify(mapper).markPublished(eq(event.getId()), any(), any());
    }

    @Test
    void releases_the_lease_when_the_publisher_fails() {
        TicketOutboxEventMapper mapper = mock(TicketOutboxEventMapper.class);
        TicketOutboxEventPublisher publisher = event -> {
            throw new IllegalStateException("broker is unavailable");
        };
        TicketOutboxEventEntity event = new TicketOutboxEventEntity();
        event.setId(UUID.fromString("009e3cce-8f4d-448d-a060-6ce2624eac77"));
        when(mapper.claimNextUnpublished(anyInt(), any(), any(), any()))
                .thenReturn(List.of(event));

        int published = new TicketOutboxDeliveryService(
                mapper,
                publisher,
                Clock.systemUTC()
        ).deliverNextBatch(1);

        assertThat(published).isZero();
        verify(mapper).releaseAfterFailure(
                eq(event.getId()),
                any(),
                eq("outbox-publisher-failed")
        );
    }
}
