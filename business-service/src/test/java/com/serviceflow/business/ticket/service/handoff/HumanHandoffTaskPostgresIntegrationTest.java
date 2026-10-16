package com.serviceflow.business.ticket.service.handoff;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.auth.dto.req.LoginRequest;
import com.serviceflow.business.auth.service.AuthService;
import com.serviceflow.business.ticket.dto.req.CreateHumanHandoffTaskRequest;
import com.serviceflow.business.ticket.domain.HumanHandoffTaskStatus;

/** Explicit VM smoke: verifies Flyway V10, UUID binding, mapper XML, and state transitions. */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = "spring.autoconfigure.exclude="
)
@ActiveProfiles("db")
@Transactional
@EnabledIfEnvironmentVariable(named = "RUN_POSTGRES_INTEGRATION_TESTS", matches = "true")
class HumanHandoffTaskPostgresIntegrationTest {

    @Autowired
    private HumanHandoffTaskService handoffTaskService;

    @Autowired
    private AuthService authService;

    @Test
    void authenticates_the_documented_local_student_account() {
        assertThat(authService.login(new LoginRequest("student", "student-pass")).accessToken())
                .isNotBlank();
    }

    @Test
    void persists_idempotently_then_claims_and_resolves_a_task() {
        UUID requestId = UUID.randomUUID();
        CreateHumanHandoffTaskRequest request = new CreateHumanHandoffTaskRequest(
                requestId,
                "account_security_risk"
        );

        var created = handoffTaskService.createForRequester("student-handoff-smoke", request);
        var repeated = handoffTaskService.createForRequester("student-handoff-smoke", request);
        var claimed = handoffTaskService.claim(created.id(), "support-handoff-smoke");
        var resolved = handoffTaskService.resolve(created.id(), "support-handoff-smoke");

        assertThat(created.status()).isEqualTo(HumanHandoffTaskStatus.PENDING);
        assertThat(repeated.id()).isEqualTo(created.id());
        assertThat(claimed.status()).isEqualTo(HumanHandoffTaskStatus.CLAIMED);
        assertThat(claimed.assignedTo()).isEqualTo("support-handoff-smoke");
        assertThat(resolved.status()).isEqualTo(HumanHandoffTaskStatus.RESOLVED);
    }
}
