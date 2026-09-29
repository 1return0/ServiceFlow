package com.serviceflow.business.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record LoginRequest(
        @NotBlank(message = "username must not be blank")
        @Size(max = 64, message = "username must be at most 64 characters")
        String username,
        @NotBlank(message = "password must not be blank")
        @Size(max = 128, message = "password must be at most 128 characters")
        String password
) {
}
