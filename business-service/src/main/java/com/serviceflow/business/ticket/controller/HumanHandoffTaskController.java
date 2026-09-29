package com.serviceflow.business.ticket.controller;

import java.util.List;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.serviceflow.business.common.Result;
import com.serviceflow.business.ticket.dto.CreateHumanHandoffTaskRequest;
import com.serviceflow.business.ticket.handoff.HumanHandoffTaskService;
import com.serviceflow.business.ticket.vo.HumanHandoffTaskResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/v1/handoffs")
@RequiredArgsConstructor
public class HumanHandoffTaskController {
    private final HumanHandoffTaskService handoffTaskService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasRole('STUDENT')")
    public Result<HumanHandoffTaskResponse> create(
            @Valid @RequestBody CreateHumanHandoffTaskRequest request,
            Authentication authentication
    ) {
        return Result.success(handoffTaskService.createForRequester(authentication.getName(), request));
    }

    @GetMapping("/admin")
    @PreAuthorize("hasAnyRole('SUPPORT_AGENT', 'ADMIN')")
    public Result<List<HumanHandoffTaskResponse>> listOpen() {
        return Result.success(handoffTaskService.listOpenTasks());
    }

    @PatchMapping("/{taskId}/claim")
    @PreAuthorize("hasAnyRole('SUPPORT_AGENT', 'ADMIN')")
    public Result<HumanHandoffTaskResponse> claim(@PathVariable UUID taskId, Authentication authentication) {
        return Result.success(handoffTaskService.claim(taskId, authentication.getName()));
    }

    @PatchMapping("/{taskId}/resolve")
    @PreAuthorize("hasAnyRole('SUPPORT_AGENT', 'ADMIN')")
    public Result<HumanHandoffTaskResponse> resolve(@PathVariable UUID taskId, Authentication authentication) {
        return Result.success(handoffTaskService.resolve(taskId, authentication.getName()));
    }
}
