package com.serviceflow.business.api;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class SystemController {

    @GetMapping("/health")
    public HealthResponse health() {
        return new HealthResponse("UP", "eduops-business", "0.1.0");
    }

    @GetMapping("/meta")
    public ServiceMetadataResponse metadata() {
        return new ServiceMetadataResponse(
                "bootstrap",
                List.of(
                        "service-request-facts",
                        "priority-and-sla-calculation",
                        "authorization",
                        "state-transitions",
                        "approval-and-audit"
                ),
                List.of(
                        "llm-determined-priority-or-sla",
                        "llm-authorized-writes",
                        "unapproved-external-actions"
                ),
                true
        );
    }

    public record HealthResponse(String status, String service, String version) {
    }

    public record ServiceMetadataResponse(
            String stage,
            List<String> authoritativeResponsibilities,
            List<String> prohibitedDelegations,
            boolean syntheticDataOnly
    ) {
    }
}
