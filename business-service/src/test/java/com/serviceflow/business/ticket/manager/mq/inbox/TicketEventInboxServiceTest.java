package com.serviceflow.business.ticket.manager.mq.inbox;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;

import com.serviceflow.business.ticket.dao.entity.TicketEventInboxEntity;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;

class TicketEventInboxServiceTest {

    private final TicketEventInboxMapper inboxMapper = Mockito.mock(
            TicketEventInboxMapper.class
    );
    private final TicketEventInboxService service = new TicketEventInboxService(
            inboxMapper
    );

    @Test
    void records_a_first_delivery() {
        TicketEventInboxMessage message = message();
        when(inboxMapper.insertIfAbsent(any(TicketEventInboxEntity.class))).thenReturn(1);

        TicketEventInboxRecordResult result = service.recordIfFirstSeen(message);

        assertThat(result.created()).isTrue();
        ArgumentCaptor<TicketEventInboxEntity> captor = ArgumentCaptor.forClass(
                TicketEventInboxEntity.class
        );
        verify(inboxMapper).insertIfAbsent(captor.capture());
        assertThat(captor.getValue().getEventId()).isEqualTo(message.eventId());
        assertThat(captor.getValue().getPayload()).isEqualTo(message.payload());
    }

    @Test
    void treats_a_duplicate_primary_key_as_an_idempotent_redelivery() {
        when(inboxMapper.insertIfAbsent(any(TicketEventInboxEntity.class))).thenReturn(0);

        TicketEventInboxRecordResult result = service.recordIfFirstSeen(message());

        assertThat(result.created()).isFalse();
    }

    @Test
    void rejects_an_unexpected_mapper_result() {
        when(inboxMapper.insertIfAbsent(any(TicketEventInboxEntity.class))).thenReturn(2);

        assertThatThrownBy(() -> service.recordIfFirstSeen(message()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("ticket inbox insert returned an unexpected row count: 2");
    }

    private static TicketEventInboxMessage message() {
        return new TicketEventInboxMessage(
                UUID.fromString("11111111-1111-1111-1111-111111111111"),
                "ticket.status_changed.v1",
                "ticket",
                UUID.fromString("22222222-2222-2222-2222-222222222222"),
                "{\"ticketId\":\"22222222-2222-2222-2222-222222222222\"}"
        );
    }
}
