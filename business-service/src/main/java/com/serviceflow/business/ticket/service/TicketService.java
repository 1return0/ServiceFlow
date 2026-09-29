package com.serviceflow.business.ticket.service;

import java.util.UUID;

import com.serviceflow.business.ticket.dto.CreateTicketRequest;
import com.serviceflow.business.ticket.dto.UpdateTicketStatusRequest;
import com.serviceflow.business.ticket.enums.OperatorRole;
import com.serviceflow.business.ticket.vo.TicketResponse;
import com.serviceflow.business.common.PageResponse;

public interface TicketService {

    TicketResponse createTicket(String requesterReference, CreateTicketRequest request);

    TicketResponse getTicketById(
            UUID ticketId,
            String actorReference,
            OperatorRole operatorRole
    );

    PageResponse<TicketResponse> listMyTickets(String requesterReference, long page, long size);

    PageResponse<TicketResponse> listWorkQueue(
            OperatorRole operatorRole,
            com.serviceflow.business.ticket.enums.TicketStatus status,
            long page,
            long size
    );

    TicketResponse claimTicket(UUID ticketId, String operatorReference, OperatorRole operatorRole);
    TicketResponse closeTicket(UUID ticketId, String requesterReference);

    TicketResponse updateTicketStatus(
            UUID ticketId,
            UpdateTicketStatusRequest request,
            OperatorRole operatorRole
    );
    TicketResponse updateTicketStatus(UUID ticketId, UpdateTicketStatusRequest request, String operatorReference, OperatorRole operatorRole);
}
