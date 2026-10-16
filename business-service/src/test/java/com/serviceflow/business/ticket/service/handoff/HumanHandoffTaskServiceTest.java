package com.serviceflow.business.ticket.service.handoff;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.serviceflow.business.ticket.dto.req.CreateHumanHandoffTaskRequest;
import com.serviceflow.business.ticket.dao.entity.HumanHandoffTaskEntity;
import com.serviceflow.business.ticket.domain.HumanHandoffTaskStatus;
import com.serviceflow.business.ticket.exception.HumanHandoffTaskTransitionNotAllowedException;
import com.serviceflow.business.ticket.dao.mapper.HumanHandoffTaskMapper;

/** Unit tests protect the task state rules without requiring PostgreSQL. */
@ExtendWith(MockitoExtension.class)
class HumanHandoffTaskServiceTest {

    @Mock
    private HumanHandoffTaskMapper handoffTaskMapper;

    @InjectMocks
    private HumanHandoffTaskService handoffTaskService;

    @Test
    void returns_the_existing_task_for_the_same_agent_request_id() {
        UUID requestId = UUID.randomUUID();
        HumanHandoffTaskEntity existing = task(requestId, HumanHandoffTaskStatus.PENDING);
        when(handoffTaskMapper.selectOne(any())).thenReturn(existing);

        var result = handoffTaskService.createForRequester(
                "student-001",
                new CreateHumanHandoffTaskRequest(requestId, "account_security_risk")
        );

        assertThat(result.id()).isEqualTo(existing.getId());
        assertThat(result.status()).isEqualTo(HumanHandoffTaskStatus.PENDING);
        verify(handoffTaskMapper, never()).insert(any(HumanHandoffTaskEntity.class));
    }

    @Test
    void claims_a_pending_task_through_an_atomic_mapper_update() {
        UUID taskId = UUID.randomUUID();
        HumanHandoffTaskEntity claimed = task(UUID.randomUUID(), HumanHandoffTaskStatus.CLAIMED);
        claimed.setId(taskId);
        claimed.setAssignedTo("support");
        when(handoffTaskMapper.claimPending(eq(taskId), eq("support"), any(Instant.class))).thenReturn(1);
        when(handoffTaskMapper.selectById(taskId)).thenReturn(claimed);

        var result = handoffTaskService.claim(taskId, "support");

        assertThat(result.status()).isEqualTo(HumanHandoffTaskStatus.CLAIMED);
        assertThat(result.assignedTo()).isEqualTo("support");
    }

    @Test
    void rejects_resolving_a_task_that_is_not_claimed_by_the_operator() {
        UUID taskId = UUID.randomUUID();
        when(handoffTaskMapper.resolveClaimed(eq(taskId), eq("support"), any(Instant.class))).thenReturn(0);

        assertThatThrownBy(() -> handoffTaskService.resolve(taskId, "support"))
                .isInstanceOf(HumanHandoffTaskTransitionNotAllowedException.class);
    }

    private HumanHandoffTaskEntity task(UUID requestId, HumanHandoffTaskStatus status) {
        return new HumanHandoffTaskEntity(
                UUID.randomUUID(), requestId, "student-001", "account_security_risk", status,
                null, Instant.parse("2026-09-22T08:00:00Z"), null, null, 0L
        );
    }
}
