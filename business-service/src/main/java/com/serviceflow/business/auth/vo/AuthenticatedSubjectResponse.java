package com.serviceflow.business.auth.vo;

import java.util.List;

/**
 * Minimal identity assertion produced only after the Java service verified a
 * Bearer JWT. It deliberately excludes the token and password information.
 */
public record AuthenticatedSubjectResponse(
        String subject,
        List<String> roles
) {
}
