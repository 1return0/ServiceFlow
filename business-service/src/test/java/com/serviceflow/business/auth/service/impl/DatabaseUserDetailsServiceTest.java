package com.serviceflow.business.auth.service.impl;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.userdetails.UserDetails;

import com.serviceflow.business.auth.entity.AccountUserEntity;
import com.serviceflow.business.auth.mapper.AccountUserMapper;

@ExtendWith(MockitoExtension.class)
class DatabaseUserDetailsServiceTest {

    @Mock
    private AccountUserMapper accountUserMapper;

    @Test
    void maps_a_persisted_account_to_spring_security_user_details() {
        AccountUserEntity account = new AccountUserEntity(
                UUID.randomUUID(),
                "support",
                "$2b$12$jbjSPCyfx7.QDAe9fjtpp.DCo1k2CQ0fNEkUOGkixB8OBWNkWdwtm",
                "SUPPORT_AGENT",
                true,
                Instant.now(),
                Instant.now(),
                0L
        );
        when(accountUserMapper.selectOne(any())).thenReturn(account);

        UserDetails details = new DatabaseUserDetailsService(accountUserMapper)
                .loadUserByUsername("support");

        assertTrue(details.isEnabled());
        assertTrue(details.getAuthorities().stream()
                .anyMatch(authority -> authority.getAuthority()
                        .equals("ROLE_SUPPORT_AGENT")));
        assertFalse(details.getPassword().contains("support-pass"));
    }
}
