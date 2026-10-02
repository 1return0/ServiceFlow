package com.serviceflow.business.auth.controller;

import java.util.Comparator;

import jakarta.validation.Valid;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.serviceflow.business.auth.dto.LoginRequest;
import com.serviceflow.business.auth.service.AuthService;
import com.serviceflow.business.auth.vo.LoginResponse;
import com.serviceflow.business.auth.vo.AuthenticatedSubjectResponse;
import com.serviceflow.business.common.Result;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return Result.success(authService.login(request));
    }

    /**
     * Python callers use this endpoint instead of decoding a forwarded JWT.
     * Java remains the sole JWT verification and authority source.
     */
    @GetMapping("/me")
    public Result<AuthenticatedSubjectResponse> currentSubject(
            Authentication authentication
    ) {
        var roles = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .filter(authority -> authority.startsWith("ROLE_"))
                .map(authority -> authority.substring("ROLE_".length()))
                .sorted(Comparator.naturalOrder())
                .toList();
        return Result.success(new AuthenticatedSubjectResponse(
                authentication.getName(),
                roles
        ));
    }
}
