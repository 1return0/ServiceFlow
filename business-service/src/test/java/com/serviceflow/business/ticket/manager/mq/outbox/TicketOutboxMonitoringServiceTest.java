package com.serviceflow.business.ticket.manager.mq.outbox;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import org.junit.jupiter.api.Test;

import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;

class TicketOutboxMonitoringServiceTest {

    @Test
    void summarizes_pending_active_and_retryable_delivery_states_without_payloads() {
        TicketOutboxEventMapper mapper = mock(TicketOutboxEventMapper.class);
        TicketOutboxEventEntity oldestPending = new TicketOutboxEventEntity();
        Instant createdAt = Instant.parse("2026-09-15T08:00:00Z");
        oldestPending.setCreatedAt(createdAt);
        when(mapper.selectCount(any())).thenReturn(5L, 2L, 1L);
        when(mapper.selectOne(any())).thenReturn(oldestPending);

        TicketOutboxDeliverySummary summary = new TicketOutboxMonitoringService(
                mapper,
                Clock.fixed(Instant.parse("2026-09-15T09:00:00Z"), ZoneOffset.UTC)
        ).getDeliverySummary();

        assertThat(summary.pendingEvents()).isEqualTo(5L);
        assertThat(summary.activelyLeasedEvents()).isEqualTo(2L);
        assertThat(summary.retryableFailedEvents()).isEqualTo(1L);
        assertThat(summary.oldestPendingCreatedAt()).isEqualTo(createdAt);
    }
}
