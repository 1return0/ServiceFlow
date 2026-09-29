package com.serviceflow.business.ticket.dto;

import java.util.UUID;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateHumanHandoffTaskRequest(
        @NotNull UUID requestId,
        @NotBlank String handoffReason
) {
}
