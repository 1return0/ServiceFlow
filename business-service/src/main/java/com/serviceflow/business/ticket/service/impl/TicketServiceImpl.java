package com.serviceflow.business.ticket.service.impl;

import java.time.Instant;
import java.util.UUID;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.serviceflow.business.ticket.dto.req.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.req.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.dao.entity.TicketEntity;
import com.serviceflow.business.ticket.domain.TicketStatus;
import com.serviceflow.business.ticket.domain.OperatorRole;
import com.serviceflow.business.ticket.exception.TicketAuthorizationException;
import com.serviceflow.business.ticket.exception.TicketNotFoundException;
import com.serviceflow.business.ticket.exception.TicketStatusTransitionNotAllowedException;
import com.serviceflow.business.ticket.exception.TicketUpdateConflictException;
import com.serviceflow.business.ticket.dao.mapper.TicketMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.ticket.service.TicketService;
import com.serviceflow.business.ticket.service.TicketStatusTransitionPolicy;
import com.serviceflow.business.ticket.service.TicketAuthorizationService;
import com.serviceflow.business.ticket.service.TicketOutboxEventFactory;
import com.serviceflow.business.ticket.dto.resp.TicketResponse;
import com.serviceflow.business.common.PageResponse;

@Service
public class TicketServiceImpl implements TicketService {

    private final TicketMapper ticketMapper;
    private final TicketStatusTransitionPolicy transitionPolicy;
    private final TicketAuthorizationService authorizationService;
    private final TicketOutboxEventMapper ticketOutboxEventMapper;
    private final TicketOutboxEventFactory ticketOutboxEventFactory;

    public TicketServiceImpl(
            TicketMapper ticketMapper,
            TicketStatusTransitionPolicy transitionPolicy,
            TicketAuthorizationService authorizationService,
            TicketOutboxEventMapper ticketOutboxEventMapper,
            TicketOutboxEventFactory ticketOutboxEventFactory
    ) {
        this.ticketMapper = ticketMapper;
        this.transitionPolicy = transitionPolicy;
        this.authorizationService = authorizationService;
        this.ticketOutboxEventMapper = ticketOutboxEventMapper;
        this.ticketOutboxEventFactory = ticketOutboxEventFactory;
    }

    @Override
    @Transactional
    public TicketResponse createTicket(
            String requesterReference,
            CreateTicketRequest request
    ) {
        if (requesterReference == null || requesterReference.isBlank()) {
            throw new IllegalArgumentException("authenticated requester reference is required");
        }
        TicketEntity ticket = new TicketEntity(
                UUID.randomUUID(),
                requesterReference.trim(),
                request.category(),
                request.summary().trim(),
                Instant.now(),
                TicketStatus.OPEN,
                0L
        );
        int insertedRows = ticketMapper.insert(ticket);
        if (insertedRows != 1) {
            throw new IllegalStateException("ticket insert did not affect exactly one row");
        }
        return TicketResponse.from(ticket);
    }

    @Override
    @Transactional(readOnly = true)
    public TicketResponse getTicketById(
            UUID ticketId,
            String actorReference,
            OperatorRole operatorRole
    ) {
        TicketEntity ticket = ticketMapper.selectById(ticketId);
        if (ticket == null || !authorizationService.canReadTicket(
                operatorRole,
                actorReference,
                ticket.getRequesterReference()
        )) {
            // Return the same result for a missing ticket and a ticket that this
            // caller may not see, so a student cannot probe other ticket IDs.
            throw new TicketNotFoundException(ticketId);
        }
        return TicketResponse.from(ticket);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<TicketResponse> listMyTickets(String requesterReference, long page, long size) {
        if (requesterReference == null || requesterReference.isBlank()) {
            throw new IllegalArgumentException("authenticated requester reference is required");
        }
        if (page < 1 || size < 1 || size > 50) {
            throw new IllegalArgumentException("ticket page must be positive and size must be between 1 and 50");
        }
        String requester = requesterReference.trim();
        var records = ticketMapper.selectPageByRequester(requester, size, (page - 1) * size);
        return new PageResponse<>(
                page, size, ticketMapper.countByRequester(requester),
                records.stream().map(TicketResponse::from).toList()
        );
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<TicketResponse> listWorkQueue(
            OperatorRole operatorRole, TicketStatus status, long page, long size
    ) {
        if (operatorRole != OperatorRole.SUPPORT_AGENT && operatorRole != OperatorRole.ADMIN) {
            throw new TicketAuthorizationException(operatorRole);
        }
        if (page < 1 || size < 1 || size > 50) {
            throw new IllegalArgumentException("ticket page must be positive and size must be between 1 and 50");
        }
        Page<TicketEntity> result = ticketMapper.selectPage(
                Page.of(page, size),
                new LambdaQueryWrapper<TicketEntity>()
                        .eq(status != null, TicketEntity::getStatus, status)
                        .orderByDesc(TicketEntity::getSubmittedAt)
                        .orderByDesc(TicketEntity::getId)
        );
        return new PageResponse<>(
                result.getCurrent(), result.getSize(), result.getTotal(),
                result.getRecords().stream().map(TicketResponse::from).toList()
        );
    }

    @Override
    @Transactional
    public TicketResponse claimTicket(UUID ticketId, String operatorReference, OperatorRole operatorRole) {
        if (operatorRole != OperatorRole.SUPPORT_AGENT && operatorRole != OperatorRole.ADMIN) throw new TicketAuthorizationException(operatorRole);
        int changed = ticketMapper.claimOpenTicket(ticketId, operatorReference, Instant.now());
        if (changed != 1) throw new TicketUpdateConflictException(ticketId);
        TicketEntity claimed = ticketMapper.selectById(ticketId);
        if (ticketOutboxEventMapper.insert(ticketOutboxEventFactory.claimed(claimed)) != 1) {
            throw new IllegalStateException("ticket claim outbox insert did not affect exactly one row");
        }
        return TicketResponse.from(claimed);
    }

    @Override
    @Transactional
    public TicketResponse closeTicket(UUID ticketId, String requesterReference) {
        TicketEntity ticket = ticketMapper.selectById(ticketId);
        if (ticket == null || !ticket.getRequesterReference().equals(requesterReference)) throw new TicketNotFoundException(ticketId);
        if (ticket.getStatus() != TicketStatus.RESOLVED) throw new TicketStatusTransitionNotAllowedException(ticket.getStatus(), TicketStatus.CLOSED);
        ticket.setStatus(TicketStatus.CLOSED);
        if (ticketMapper.updateById(ticket) != 1) throw new TicketUpdateConflictException(ticketId);
        ticketOutboxEventMapper.insert(ticketOutboxEventFactory.statusChanged(ticket));
        return TicketResponse.from(ticket);
    }

    @Override
    @Transactional
    public TicketResponse updateTicketStatus(
            UUID ticketId,
            UpdateTicketStatusRequest request,
            OperatorRole operatorRole
    ) {
        return updateTicketStatus(ticketId, request, null, operatorRole);
    }

    @Override
    @Transactional
    public TicketResponse updateTicketStatus(
            UUID ticketId, UpdateTicketStatusRequest request,
            String operatorReference, OperatorRole operatorRole
    ) {
        if (!authorizationService.canUpdateStatus(operatorRole)) {
            throw new TicketAuthorizationException(operatorRole);
        }
        TicketEntity ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) {
            throw new TicketNotFoundException(ticketId);
        }
        if (operatorRole == OperatorRole.SUPPORT_AGENT
                && (operatorReference == null || !operatorReference.equals(ticket.getAssigneeReference()))) {
            throw new TicketAuthorizationException(operatorRole);
        }
        if (!transitionPolicy.isAllowed(ticket.getStatus(), request.targetStatus())) {
            throw new TicketStatusTransitionNotAllowedException(
                    ticket.getStatus(),
                    request.targetStatus()
            );
        }

        ticket.setStatus(request.targetStatus());
        int updatedRows = ticketMapper.updateById(ticket);
        if (updatedRows != 1) {
            throw new TicketUpdateConflictException(ticketId);
        }
        int insertedOutboxRows = ticketOutboxEventMapper.insert(
                ticketOutboxEventFactory.statusChanged(ticket)
        );
        if (insertedOutboxRows != 1) {
            throw new IllegalStateException("ticket outbox insert did not affect exactly one row");
        }
        return TicketResponse.from(ticket);
    }
}
