package com.serviceflow.business.ticket.dto.resp;

import java.time.Instant;
import java.util.UUID;

import com.serviceflow.business.ticket.dao.entity.HumanHandoffTaskEntity;
import com.serviceflow.business.ticket.domain.HumanHandoffTaskStatus;

public record HumanHandoffTaskResponse(
        UUID id, UUID requestId, String requesterReference, String handoffReason,
        HumanHandoffTaskStatus status, String assignedTo, Instant createdAt,
        Instant claimedAt, Instant resolvedAt, Long version
) {
    public static HumanHandoffTaskResponse from(HumanHandoffTaskEntity entity) {
        return new HumanHandoffTaskResponse(entity.getId(), entity.getRequestId(), entity.getRequesterReference(),
                entity.getHandoffReason(), entity.getStatus(), entity.getAssignedTo(), entity.getCreatedAt(),
                entity.getClaimedAt(), entity.getResolvedAt(), entity.getVersion());
    }
}
