package com.serviceflow.business.auth.service;

import com.serviceflow.business.auth.dto.req.LoginRequest;
import com.serviceflow.business.auth.dto.resp.LoginResponse;

public interface AuthService {

    LoginResponse login(LoginRequest request);
}
