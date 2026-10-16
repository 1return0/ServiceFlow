package com.serviceflow.business.ticket.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.auth.dao.entity.AccountUserEntity;
import com.serviceflow.business.auth.dto.req.LoginRequest;
import com.serviceflow.business.auth.dao.mapper.AccountUserMapper;
import com.serviceflow.business.auth.service.AuthService;
import com.serviceflow.business.ticket.dto.req.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.req.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.domain.OperatorRole;
import com.serviceflow.business.ticket.domain.ServiceRequestCategory;
import com.serviceflow.business.ticket.domain.TicketStatus;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;

/** Requires the student's local PostgreSQL profile; each test transaction is rolled back. */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = "spring.autoconfigure.exclude="
)
@ActiveProfiles("db")
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

    @Autowired
    private AccountUserMapper accountUserMapper;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private AuthService authService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void persists_ticket_update_and_pending_outbox_event_in_one_postgres_transaction()
            throws Exception {
        AccountUserEntity supportAccount = accountUserMapper.selectOne(
                new LambdaQueryWrapper<AccountUserEntity>()
                        .eq(AccountUserEntity::getUsername, "support")
        );
        assertThat(supportAccount).isNotNull();
        assertThat(passwordEncoder.matches(
                "support-pass",
                "{bcrypt}" + supportAccount.getPasswordHash()
        )).isTrue();
        assertThat(authService.login(new LoginRequest(
                "support",
                "support-pass"
        )).accessToken()).isNotBlank();

        var created = ticketService.createTicket("outbox-integration-student", new CreateTicketRequest(
                ServiceRequestCategory.CAMPUS_NETWORK,
                "Verify atomic ticket and outbox persistence"
        ));
        ticketService.claimTicket(
                created.id(),
                "support",
                OperatorRole.SUPPORT_AGENT
        );
        var updated = ticketService.updateTicketStatus(
                created.id(),
                new UpdateTicketStatusRequest(TicketStatus.IN_PROGRESS),
                "support",
                OperatorRole.SUPPORT_AGENT
        );

        var events = ticketOutboxEventMapper.selectList(
                new LambdaQueryWrapper<TicketOutboxEventEntity>()
                        .eq(TicketOutboxEventEntity::getAggregateId, created.id())
        );
        TicketOutboxEventEntity event = events.stream()
                .filter(candidate -> candidate.getEventType().equals("ticket.status_changed.v1"))
                .findFirst()
                .orElseThrow();

        assertThat(updated.status()).isEqualTo(TicketStatus.IN_PROGRESS);
        assertThat(updated.version()).isEqualTo(1L);
        assertThat(events).hasSize(2);
        assertThat(event).isNotNull();
        assertThat(event.getEventType()).isEqualTo("ticket.status_changed.v1");
        assertThat(objectMapper.readTree(event.getPayload())
                .path("status")
                .asText()).isEqualTo("IN_PROGRESS");
        assertThat(event.getPublishedAt()).isNull();
        assertThat(event.getPublishAttempts()).isZero();
    }
}
