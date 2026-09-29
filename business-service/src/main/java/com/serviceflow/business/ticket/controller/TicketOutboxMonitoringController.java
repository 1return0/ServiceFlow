package com.serviceflow.business.ticket.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.serviceflow.business.common.Result;
import com.serviceflow.business.ticket.outbox.TicketOutboxDeliverySummary;
import com.serviceflow.business.ticket.outbox.TicketOutboxMonitoringService;
import lombok.RequiredArgsConstructor;

/** Administrator-only delivery health view; event payloads remain internal. */
@RestController
@RequestMapping("/api/v1/admin/outbox")
@RequiredArgsConstructor
public class TicketOutboxMonitoringController {

    private final TicketOutboxMonitoringService monitoringService;

    @GetMapping("/summary")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<TicketOutboxDeliverySummary> getDeliverySummary() {
        return Result.success(monitoringService.getDeliverySummary());
    }
}
