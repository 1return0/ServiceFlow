package com.serviceflow.business.auth.config;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;
import org.springframework.validation.annotation.Validated;

/** Local JWT settings. Production secrets must come from deployment configuration. */
@Getter
@Setter
@Validated
@Component
@ConfigurationProperties(prefix = "eduops.security.jwt")
public class JwtProperties {

    @NotBlank
    private String secret;

    @Min(60)
    private long accessTokenTtlSeconds;
}
