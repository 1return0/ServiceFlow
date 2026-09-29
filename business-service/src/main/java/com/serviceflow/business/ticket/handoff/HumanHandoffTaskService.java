package com.serviceflow.business.ticket.handoff;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.serviceflow.business.ticket.dto.CreateHumanHandoffTaskRequest;
import com.serviceflow.business.ticket.entity.HumanHandoffTaskEntity;
import com.serviceflow.business.ticket.enums.HumanHandoffTaskStatus;
import com.serviceflow.business.ticket.exception.HumanHandoffTaskNotFoundException;
import com.serviceflow.business.ticket.exception.HumanHandoffTaskTransitionNotAllowedException;
import com.serviceflow.business.ticket.mapper.HumanHandoffTaskMapper;
import com.serviceflow.business.ticket.vo.HumanHandoffTaskResponse;
import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class HumanHandoffTaskService {
    private final HumanHandoffTaskMapper handoffTaskMapper;

    @Transactional
    public HumanHandoffTaskResponse createForRequester(String requesterReference, CreateHumanHandoffTaskRequest request) {
        String requester = requireIdentity(requesterReference);
        HumanHandoffTaskEntity existing = handoffTaskMapper.selectOne(Wrappers.<HumanHandoffTaskEntity>lambdaQuery()
                .eq(HumanHandoffTaskEntity::getRequestId, request.requestId()));
        if (existing != null) {
            return HumanHandoffTaskResponse.from(existing);
        }
        HumanHandoffTaskEntity task = new HumanHandoffTaskEntity(UUID.randomUUID(), request.requestId(), requester,
                normalizeReason(request.handoffReason()), HumanHandoffTaskStatus.PENDING, null, Instant.now(), null, null, 0L);
        if (handoffTaskMapper.insert(task) != 1) {
            throw new IllegalStateException("human handoff task insert did not affect one row");
        }
        return HumanHandoffTaskResponse.from(task);
    }

    @Transactional(readOnly = true)
    public List<HumanHandoffTaskResponse> listOpenTasks() {
        return handoffTaskMapper.selectList(Wrappers.<HumanHandoffTaskEntity>lambdaQuery()
                        .ne(HumanHandoffTaskEntity::getStatus, HumanHandoffTaskStatus.RESOLVED)
                        .orderByAsc(HumanHandoffTaskEntity::getCreatedAt))
                .stream().map(HumanHandoffTaskResponse::from).toList();
    }

    @Transactional
    public HumanHandoffTaskResponse claim(UUID taskId, String assignee) {
        if (handoffTaskMapper.claimPending(taskId, requireIdentity(assignee), Instant.now()) != 1) {
            throw new HumanHandoffTaskTransitionNotAllowedException(taskId);
        }
        return requireTask(taskId);
    }

    @Transactional
    public HumanHandoffTaskResponse resolve(UUID taskId, String assignee) {
        if (handoffTaskMapper.resolveClaimed(taskId, requireIdentity(assignee), Instant.now()) != 1) {
            throw new HumanHandoffTaskTransitionNotAllowedException(taskId);
        }
        return requireTask(taskId);
    }

    private HumanHandoffTaskResponse requireTask(UUID taskId) {
        HumanHandoffTaskEntity task = handoffTaskMapper.selectById(taskId);
        if (task == null) throw new HumanHandoffTaskNotFoundException(taskId);
        return HumanHandoffTaskResponse.from(task);
    }

    private String requireIdentity(String value) {
        if (value == null || value.isBlank()) throw new IllegalArgumentException("authenticated identity is required");
        return value.trim();
    }

    private String normalizeReason(String value) {
        String normalized = value == null ? "" : value.trim();
        if (!normalized.equals("account_security_risk") && !normalized.equals("physical_safety_risk")) {
            throw new IllegalArgumentException("handoff reason is not supported");
        }
        return normalized;
    }
}
