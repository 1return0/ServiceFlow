package com.serviceflow.business.auth.service;

import java.time.Instant;

public record IssuedJwt(String token, Instant expiresAt) {
}
