package com.serviceflow.business.ticket.dto;

import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** Request DTO: validates data received from an HTTP client before business processing. */
public record CreateTicketRequest(
        @NotNull ServiceRequestCategory category,
        @NotBlank @Size(max = 500) String summary
) {
}
