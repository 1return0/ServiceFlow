package com.serviceflow.business.common;

import org.springframework.context.support.DefaultMessageSourceResolvable;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.serviceflow.business.ticket.exception.TicketNotFoundException;
import com.serviceflow.business.ticket.exception.TicketAuthorizationException;
import com.serviceflow.business.ticket.exception.TicketStatusTransitionNotAllowedException;
import com.serviceflow.business.ticket.exception.TicketUpdateConflictException;
import com.serviceflow.business.ticket.exception.TicketNotificationNotFoundException;
import com.serviceflow.business.ticket.exception.HumanHandoffTaskNotFoundException;
import com.serviceflow.business.ticket.exception.HumanHandoffTaskTransitionNotAllowedException;
import com.serviceflow.business.auth.exception.InvalidLoginCredentialsException;
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(InvalidLoginCredentialsException.class)
    @ResponseStatus(HttpStatus.UNAUTHORIZED)
    public Result<Void> handleInvalidLoginCredentials(
            InvalidLoginCredentialsException exception
    ) {
        return Result.failure(HttpStatus.UNAUTHORIZED.value(), exception.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleValidation(MethodArgumentNotValidException exception) {
        String message = exception.getBindingResult().getFieldErrors().stream()
                .map(DefaultMessageSourceResolvable::getDefaultMessage)
                .findFirst()
                .orElse("request validation failed");
        return Result.failure(HttpStatus.BAD_REQUEST.value(), message);
    }

    @ExceptionHandler(TicketNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Result<Void> handleTicketNotFound(TicketNotFoundException exception) {
        return Result.failure(HttpStatus.NOT_FOUND.value(), exception.getMessage());
    }

    @ExceptionHandler(TicketNotificationNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Result<Void> handleNotificationNotFound(
            TicketNotificationNotFoundException exception
    ) {
        return Result.failure(HttpStatus.NOT_FOUND.value(), exception.getMessage());
    }

    @ExceptionHandler(HumanHandoffTaskNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Result<Void> handleHandoffNotFound(HumanHandoffTaskNotFoundException exception) {
        return Result.failure(HttpStatus.NOT_FOUND.value(), exception.getMessage());
    }

    @ExceptionHandler(HumanHandoffTaskTransitionNotAllowedException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    public Result<Void> handleHandoffTransition(HumanHandoffTaskTransitionNotAllowedException exception) {
        return Result.failure(HttpStatus.CONFLICT.value(), exception.getMessage());
    }

    @ExceptionHandler(TicketAuthorizationException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public Result<Void> handleTicketAuthorization(TicketAuthorizationException exception) {
        return Result.failure(HttpStatus.FORBIDDEN.value(), exception.getMessage());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleTypeMismatch(MethodArgumentTypeMismatchException exception) {
        return Result.failure(
                HttpStatus.BAD_REQUEST.value(),
                "invalid value for parameter: " + exception.getName()
        );
    }

    @ExceptionHandler(TicketStatusTransitionNotAllowedException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    public Result<Void> handleStatusTransitionNotAllowed(
            TicketStatusTransitionNotAllowedException exception
    ) {
        return Result.failure(HttpStatus.CONFLICT.value(), exception.getMessage());
    }

    @ExceptionHandler(TicketUpdateConflictException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    public Result<Void> handleTicketUpdateConflict(TicketUpdateConflictException exception) {
        return Result.failure(HttpStatus.CONFLICT.value(), exception.getMessage());
    }
}
