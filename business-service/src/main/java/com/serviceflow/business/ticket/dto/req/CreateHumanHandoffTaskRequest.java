package com.serviceflow.business.ticket.dto.req;

import java.util.UUID;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateHumanHandoffTaskRequest(
        @NotNull UUID requestId,
        @NotBlank String handoffReason
) {
}
