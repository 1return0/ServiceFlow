package com.serviceflow.business.ticket.notification;

import java.util.List;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.vo.TicketNotificationResponse;
import com.serviceflow.business.ticket.vo.TicketNotificationSummaryResponse;
import com.serviceflow.business.ticket.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.exception.TicketNotificationNotFoundException;
import lombok.RequiredArgsConstructor;

/** Reads only notifications owned by the authenticated requester identity. */
@Service
@RequiredArgsConstructor
public class TicketNotificationQueryService {

    private static final int MAX_LIMIT = 50;

    private final TicketNotificationMapper notificationMapper;

    @Transactional(readOnly = true)
    public List<TicketNotificationResponse> listForRequester(
            String requesterReference,
            int limit
    ) {
        if (requesterReference == null || requesterReference.isBlank()) {
            throw new IllegalArgumentException("authenticated requester reference is required");
        }
        if (limit < 1 || limit > MAX_LIMIT) {
            throw new IllegalArgumentException("notification limit must be between 1 and 50");
        }
        return notificationMapper.selectRecentByRecipient(
                        requesterReference.trim(),
                        limit
                ).stream()
                .map(TicketNotificationResponse::from)
                .toList();
    }

    @Transactional
    public TicketNotificationResponse markAsRead(
            String requesterReference,
            UUID notificationId
    ) {
        String normalizedRequester = requireRequesterReference(requesterReference);
        TicketNotificationEntity existing = notificationMapper.selectByIdAndRecipient(
                notificationId,
                normalizedRequester
        );
        if (existing == null) {
            throw new TicketNotificationNotFoundException(notificationId);
        }
        if (existing.getReadAt() != null) {
            return TicketNotificationResponse.from(existing);
        }

        // PostgreSQL TIMESTAMPTZ persists microsecond precision. Normalize before
        // returning so the first and a repeated idempotent read have one stable value.
        Instant readAt = Instant.now().truncatedTo(ChronoUnit.MICROS);
        int updatedRows = notificationMapper.markReadIfUnread(
                notificationId,
                normalizedRequester,
                readAt
        );
        if (updatedRows == 1) {
            existing.setReadAt(readAt);
            return TicketNotificationResponse.from(existing);
        }

        TicketNotificationEntity current = notificationMapper.selectByIdAndRecipient(
                notificationId,
                normalizedRequester
        );
        if (current == null) {
            throw new TicketNotificationNotFoundException(notificationId);
        }
        if (current.getReadAt() != null) {
            return TicketNotificationResponse.from(current);
        }
        throw new IllegalStateException("notification read update did not affect exactly one row");
    }

    @Transactional(readOnly = true)
    public TicketNotificationSummaryResponse summarizeForRequester(
            String requesterReference
    ) {
        return new TicketNotificationSummaryResponse(
                notificationMapper.countUnreadByRecipient(
                        requireRequesterReference(requesterReference)
                )
        );
    }

    private String requireRequesterReference(String requesterReference) {
        if (requesterReference == null || requesterReference.isBlank()) {
            throw new IllegalArgumentException("authenticated requester reference is required");
        }
        return requesterReference.trim();
    }
}
