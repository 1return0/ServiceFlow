package com.serviceflow.business.auth.service;

import com.serviceflow.business.auth.dto.LoginRequest;
import com.serviceflow.business.auth.vo.LoginResponse;

public interface AuthService {

    LoginResponse login(LoginRequest request);
}
