package com.serviceflow.business.ticket.controller;

import java.util.List;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.serviceflow.business.common.Result;
import com.serviceflow.business.ticket.notification.TicketNotificationQueryService;
import com.serviceflow.business.ticket.vo.TicketNotificationResponse;
import com.serviceflow.business.ticket.vo.TicketNotificationSummaryResponse;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;

/** Student notification read API; the requester identity is taken from JWT, never a query parameter. */
@RestController
@RequestMapping("/api/v1/notifications")
@RequiredArgsConstructor
public class TicketNotificationController {

    private final TicketNotificationQueryService notificationQueryService;

    @GetMapping("/me")
    @PreAuthorize("hasRole('STUDENT')")
    public Result<List<TicketNotificationResponse>> listMyNotifications(
            Authentication authentication,
            @RequestParam(defaultValue = "20") @Min(1) @Max(50) int limit
    ) {
        return Result.success(notificationQueryService.listForRequester(
                authentication.getName(),
                limit
        ));
    }

    @GetMapping("/me/summary")
    @PreAuthorize("hasRole('STUDENT')")
    public Result<TicketNotificationSummaryResponse> summarizeMyNotifications(
            Authentication authentication
    ) {
        return Result.success(notificationQueryService.summarizeForRequester(
                authentication.getName()
        ));
    }

    @PatchMapping("/{notificationId}/read")
    @PreAuthorize("hasRole('STUDENT')")
    public Result<TicketNotificationResponse> markMyNotificationRead(
            @PathVariable java.util.UUID notificationId,
            Authentication authentication
    ) {
        return Result.success(notificationQueryService.markAsRead(
                authentication.getName(),
                notificationId
        ));
    }
}
