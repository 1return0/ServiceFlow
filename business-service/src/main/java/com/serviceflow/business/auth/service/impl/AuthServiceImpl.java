package com.serviceflow.business.auth.service.impl;

import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.stereotype.Service;

import com.serviceflow.business.auth.dto.req.LoginRequest;
import com.serviceflow.business.auth.exception.InvalidLoginCredentialsException;
import com.serviceflow.business.auth.service.AuthService;
import com.serviceflow.business.auth.service.IssuedJwt;
import com.serviceflow.business.auth.service.JwtTokenService;
import com.serviceflow.business.auth.dto.resp.LoginResponse;

@Service
public class AuthServiceImpl implements AuthService {

    private final AuthenticationManager authenticationManager;
    private final JwtTokenService jwtTokenService;

    public AuthServiceImpl(
            AuthenticationManager authenticationManager,
            JwtTokenService jwtTokenService
    ) {
        this.authenticationManager = authenticationManager;
        this.jwtTokenService = jwtTokenService;
    }

    @Override
    public LoginResponse login(LoginRequest request) {
        try {
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            request.username(),
                            request.password()
                    )
            );
            IssuedJwt issuedJwt = jwtTokenService.issue(authentication);
            return new LoginResponse(
                    issuedJwt.token(),
                    "Bearer",
                    issuedJwt.expiresAt()
            );
        } catch (AuthenticationException exception) {
            throw new InvalidLoginCredentialsException();
        }
    }
}
