package com.serviceflow.business.auth.exception;

public class InvalidLoginCredentialsException extends RuntimeException {

    public InvalidLoginCredentialsException() {
        super("invalid username or password");
    }
}
