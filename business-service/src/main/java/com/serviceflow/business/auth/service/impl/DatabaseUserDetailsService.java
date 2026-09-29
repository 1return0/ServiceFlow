package com.serviceflow.business.auth.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.serviceflow.business.auth.entity.AccountUserEntity;
import com.serviceflow.business.auth.mapper.AccountUserMapper;

/** Loads an enabled application account from PostgreSQL for Spring Security authentication. */
@Service
@Profile("!test")
public class DatabaseUserDetailsService implements UserDetailsService {

    private final AccountUserMapper accountUserMapper;

    public DatabaseUserDetailsService(AccountUserMapper accountUserMapper) {
        this.accountUserMapper = accountUserMapper;
    }

    @Override
    @Transactional(readOnly = true)
    public UserDetails loadUserByUsername(String username)
            throws UsernameNotFoundException {
        AccountUserEntity account = accountUserMapper.selectOne(
                new LambdaQueryWrapper<AccountUserEntity>()
                        .eq(AccountUserEntity::getUsername, username)
        );
        if (account == null) {
            throw new UsernameNotFoundException("account not found");
        }
        return User.withUsername(account.getUsername())
                .password("{bcrypt}" + account.getPasswordHash())
                .roles(account.getRoleCode())
                .disabled(!Boolean.TRUE.equals(account.getEnabled()))
                .build();
    }
}
