package com.serviceflow.business.auth.service;

import java.time.Instant;
import java.util.List;

public record VerifiedJwt(
        String subject,
        List<String> roles,
        Instant expiresAt
) {
}
