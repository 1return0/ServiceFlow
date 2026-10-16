package com.serviceflow.business.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.Test;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.serviceflow.business.common.PageResponse;
import com.serviceflow.business.ticket.dao.entity.TicketEntity;
import com.serviceflow.business.ticket.domain.ServiceRequestCategory;
import com.serviceflow.business.ticket.domain.TicketStatus;
import com.serviceflow.business.ticket.dao.mapper.TicketMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.ticket.service.impl.TicketServiceImpl;
import com.serviceflow.business.ticket.dto.resp.TicketResponse;

class TicketServiceImplTest {

    @Test
    void listsOnlyTheRequestedPageForTheAuthenticatedRequester() {
        TicketMapper ticketMapper = mock(TicketMapper.class);
        Page<TicketEntity> databasePage = new Page<>(2, 5, 11);
        databasePage.setRecords(List.of(new TicketEntity(
                UUID.randomUUID(), "student-a", ServiceRequestCategory.CAMPUS_NETWORK,
                "network unavailable", Instant.parse("2026-09-27T00:00:00Z"),
                TicketStatus.OPEN, 0L
        )));
        when(ticketMapper.selectPageByRequester("student-a", 5, 5))
                .thenReturn(databasePage.getRecords());
        when(ticketMapper.countByRequester("student-a")).thenReturn(11L);
        TicketServiceImpl service = new TicketServiceImpl(
                ticketMapper,
                mock(TicketStatusTransitionPolicy.class),
                mock(TicketAuthorizationService.class),
                mock(TicketOutboxEventMapper.class),
                mock(TicketOutboxEventFactory.class)
        );

        PageResponse<TicketResponse> response = service.listMyTickets("student-a", 2, 5);

        assertThat(response.page()).isEqualTo(2);
        assertThat(response.size()).isEqualTo(5);
        assertThat(response.total()).isEqualTo(11);
        assertThat(response.items()).extracting(TicketResponse::requesterReference)
                .containsExactly("student-a");
    }
}
