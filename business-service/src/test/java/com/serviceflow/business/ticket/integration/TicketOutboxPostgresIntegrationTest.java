package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.serviceflow.business.ticket.dto.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.enums.OperatorRole;
import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import com.serviceflow.business.ticket.enums.TicketStatus;
import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.ticket.service.TicketService;

/**
 * Opt-in real-database smoke. It is skipped unless the operator explicitly enables it.
 * The surrounding test transaction is rolled back, so it leaves no demo ticket or event.
 */
@SpringBootTest(properties = "spring.autoconfigure.exclude=")
@ActiveProfiles("local")
@Transactional
@EnabledIfEnvironmentVariable(
        named = "RUN_POSTGRES_INTEGRATION_TESTS",
        matches = "true"
)
class TicketOutboxPostgresIntegrationTest {

    @Autowired
    private TicketService ticketService;

    @Autowired
    private TicketOutboxEventMapper ticketOutboxEventMapper;

    @Test
    void persists_ticket_status_and_pending_outbox_event_in_one_transaction() throws Exception {
        var created = ticketService.createTicket("outbox-smoke-student", new CreateTicketRequest(
                ServiceRequestCategory.CAMPUS_NETWORK,
                "Outbox PostgreSQL smoke ticket"
        ));

        var updated = ticketService.updateTicketStatus(
                created.id(),
                new UpdateTicketStatusRequest(TicketStatus.IN_PROGRESS),
                OperatorRole.SUPPORT_AGENT
        );

        List<TicketOutboxEventEntity> events = ticketOutboxEventMapper.selectList(
                Wrappers.<TicketOutboxEventEntity>lambdaQuery()
                        .eq(TicketOutboxEventEntity::getAggregateId, created.id())
        );

        assertThat(updated.status()).isEqualTo(TicketStatus.IN_PROGRESS);
        assertThat(updated.version()).isEqualTo(1L);
        assertThat(events).hasSize(1);
        assertThat(events.get(0).getEventType())
                .isEqualTo("ticket.status_changed.v1");
        var payload = new ObjectMapper().readTree(events.get(0).getPayload());
        assertThat(payload.path("status").asText()).isEqualTo("IN_PROGRESS");
        assertThat(payload.path("version").asLong()).isEqualTo(1L);
        assertThat(events.get(0).getPublishedAt()).isNull();
        assertThat(events.get(0).getPublishAttempts()).isZero();
    }
}
