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
import com.serviceflow.business.auth.entity.AccountUserEntity;
import com.serviceflow.business.auth.dto.LoginRequest;
import com.serviceflow.business.auth.mapper.AccountUserMapper;
import com.serviceflow.business.auth.service.AuthService;
import com.serviceflow.business.ticket.dto.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.enums.OperatorRole;
import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import com.serviceflow.business.ticket.enums.TicketStatus;
import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;

/** Requires the student's local PostgreSQL profile; each test transaction is rolled back. */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = "spring.autoconfigure.exclude="
)
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
        var updated = ticketService.updateTicketStatus(
                created.id(),
                new UpdateTicketStatusRequest(TicketStatus.IN_PROGRESS),
                OperatorRole.SUPPORT_AGENT
        );

        TicketOutboxEventEntity event = ticketOutboxEventMapper.selectOne(
                new LambdaQueryWrapper<TicketOutboxEventEntity>()
                        .eq(TicketOutboxEventEntity::getAggregateId, created.id())
        );

        assertThat(updated.status()).isEqualTo(TicketStatus.IN_PROGRESS);
        assertThat(updated.version()).isEqualTo(1L);
        assertThat(event).isNotNull();
        assertThat(event.getEventType()).isEqualTo("ticket.status_changed.v1");
        assertThat(objectMapper.readTree(event.getPayload())
                .path("status")
                .asText()).isEqualTo("IN_PROGRESS");
        assertThat(event.getPublishedAt()).isNull();
        assertThat(event.getPublishAttempts()).isZero();
    }
}
