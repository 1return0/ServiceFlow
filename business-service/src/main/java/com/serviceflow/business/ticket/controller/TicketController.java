package com.serviceflow.business.ticket.controller;

import java.util.UUID;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;

import com.serviceflow.business.common.Result;
import com.serviceflow.business.common.PageResponse;
import com.serviceflow.business.ticket.dto.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.enums.OperatorRole;
import com.serviceflow.business.ticket.service.TicketService;
import com.serviceflow.business.ticket.vo.TicketResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

@RestController
@RequestMapping("/api/v1/tickets")
public class TicketController {

    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @PostMapping
    @PreAuthorize("hasRole('STUDENT')")
    @ResponseStatus(HttpStatus.CREATED)
    public Result<TicketResponse> createTicket(
            @Valid @RequestBody CreateTicketRequest request,
            Authentication authentication
    ) {
        return Result.success(ticketService.createTicket(
                authentication.getName(),
                request
        ));
    }

    @GetMapping("/me")
    @PreAuthorize("hasRole('STUDENT')")
    public Result<PageResponse<TicketResponse>> listMyTickets(
            Authentication authentication,
            @RequestParam(defaultValue = "1") @Min(1) long page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(50) long size
    ) {
        return Result.success(ticketService.listMyTickets(authentication.getName(), page, size));
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('SUPPORT_AGENT', 'ADMIN')")
    public Result<PageResponse<TicketResponse>> listWorkQueue(
            Authentication authentication,
            @RequestParam(required = false) com.serviceflow.business.ticket.enums.TicketStatus status,
            @RequestParam(defaultValue = "1") @Min(1) long page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(50) long size
    ) {
        return Result.success(ticketService.listWorkQueue(
                resolveOperatorRole(authentication), status, page, size
        ));
    }

    @PatchMapping("/{ticketId}/claim")
    @PreAuthorize("hasAnyRole('SUPPORT_AGENT', 'ADMIN')")
    public Result<TicketResponse> claimTicket(@PathVariable UUID ticketId, Authentication authentication) {
        return Result.success(ticketService.claimTicket(ticketId, authentication.getName(), resolveOperatorRole(authentication)));
    }

    @PatchMapping("/{ticketId}/close")
    @PreAuthorize("hasRole('STUDENT')")
    public Result<TicketResponse> closeTicket(@PathVariable UUID ticketId, Authentication authentication) {
        return Result.success(ticketService.closeTicket(ticketId, authentication.getName()));
    }

    @GetMapping("/{ticketId}")
    public Result<TicketResponse> getTicketById(
            @PathVariable UUID ticketId,
            Authentication authentication
    ) {
        return Result.success(ticketService.getTicketById(
                ticketId,
                authentication.getName(),
                resolveOperatorRole(authentication)
        ));
    }

    @PatchMapping("/{ticketId}/status")
    @PreAuthorize("hasAnyRole('SUPPORT_AGENT', 'ADMIN')")
    public Result<TicketResponse> updateTicketStatus(
            @PathVariable UUID ticketId,
            @Valid @RequestBody UpdateTicketStatusRequest request,
            Authentication authentication
    ) {
        return Result.success(ticketService.updateTicketStatus(
                ticketId,
                request,
                authentication.getName(),
                resolveOperatorRole(authentication)
        ));
    }

    private OperatorRole resolveOperatorRole(Authentication authentication) {
        var roles = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .filter(authority -> authority.startsWith("ROLE_"))
                .map(authority -> authority.substring("ROLE_".length()))
                .map(OperatorRole::valueOf)
                .collect(java.util.stream.Collectors.toSet());
        if (roles.contains(OperatorRole.ADMIN)) {
            return OperatorRole.ADMIN;
        }
        if (roles.contains(OperatorRole.SUPPORT_AGENT)) {
            return OperatorRole.SUPPORT_AGENT;
        }
        if (roles.contains(OperatorRole.STUDENT)) {
            return OperatorRole.STUDENT;
        }
        throw new IllegalStateException("authenticated role is missing");
    }
}
