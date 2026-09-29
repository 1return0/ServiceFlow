package com.serviceflow.business.ticket.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.never;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import com.serviceflow.business.ticket.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.exception.TicketNotificationNotFoundException;

class TicketNotificationQueryServiceTest {

    private final TicketNotificationMapper notificationMapper = Mockito.mock(
            TicketNotificationMapper.class
    );
    private final TicketNotificationQueryService service = new TicketNotificationQueryService(
            notificationMapper
    );

    @Test
    void reads_only_the_authenticated_requesters_recent_notifications() {
        TicketNotificationEntity notification = new TicketNotificationEntity(
                UUID.randomUUID(),
                UUID.randomUUID(),
                "student",
                UUID.randomUUID(),
                "ticket.status_changed.v1",
                "Your service ticket status is now RESOLVED.",
                Instant.parse("2026-09-18T08:00:00Z"),
                null
        );
        when(notificationMapper.selectRecentByRecipient("student", 20))
                .thenReturn(List.of(notification));

        var result = service.listForRequester("student", 20);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).ticketId()).isEqualTo(notification.getTicketId());
        verify(notificationMapper).selectRecentByRecipient("student", 20);
    }

    @Test
    void rejects_an_unbounded_notification_query() {
        assertThatThrownBy(() -> service.listForRequester("student", 51))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("notification limit must be between 1 and 50");
    }

    @Test
    void marks_an_unread_notification_once_for_its_owner() {
        TicketNotificationEntity notification = notification("student", null);
        when(notificationMapper.selectByIdAndRecipient(notification.getId(), "student"))
                .thenReturn(notification);
        when(notificationMapper.markReadIfUnread(
                org.mockito.ArgumentMatchers.eq(notification.getId()),
                org.mockito.ArgumentMatchers.eq("student"),
                org.mockito.ArgumentMatchers.any(Instant.class)
        )).thenReturn(1);

        var result = service.markAsRead("student", notification.getId());

        assertThat(result.readAt()).isNotNull();
    }

    @Test
    void treats_a_concurrent_already_read_result_as_an_idempotent_success() {
        TicketNotificationEntity unreadSnapshot = notification("student", null);
        TicketNotificationEntity currentReadRow = notification(
                "student",
                Instant.parse("2026-09-18T09:00:00Z")
        );
        currentReadRow.setId(unreadSnapshot.getId());

        when(notificationMapper.selectByIdAndRecipient(unreadSnapshot.getId(), "student"))
                .thenReturn(unreadSnapshot, currentReadRow);
        when(notificationMapper.markReadIfUnread(
                org.mockito.ArgumentMatchers.eq(unreadSnapshot.getId()),
                org.mockito.ArgumentMatchers.eq("student"),
                org.mockito.ArgumentMatchers.any(Instant.class)
        )).thenReturn(0);

        var result = service.markAsRead("student", unreadSnapshot.getId());

        assertThat(result.readAt()).isEqualTo(currentReadRow.getReadAt());
    }

    @Test
    void hides_a_notification_owned_by_another_student_as_not_found() {
        UUID notificationId = UUID.randomUUID();
        when(notificationMapper.selectByIdAndRecipient(notificationId, "student"))
                .thenReturn(null);

        assertThatThrownBy(() -> service.markAsRead("student", notificationId))
                .isInstanceOf(TicketNotificationNotFoundException.class);
        verify(notificationMapper, never()).markReadIfUnread(
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any()
        );
    }

    @Test
    void asks_postgresql_for_only_the_current_students_unread_count() {
        when(notificationMapper.countUnreadByRecipient("student")).thenReturn(4L);

        var result = service.summarizeForRequester("student");

        assertThat(result.unreadCount()).isEqualTo(4L);
        verify(notificationMapper).countUnreadByRecipient("student");
    }

    private static TicketNotificationEntity notification(
            String requesterReference,
            Instant readAt
    ) {
        return new TicketNotificationEntity(
                UUID.randomUUID(),
                UUID.randomUUID(),
                requesterReference,
                UUID.randomUUID(),
                "ticket.status_changed.v1",
                "Your service ticket status is now RESOLVED.",
                Instant.parse("2026-09-18T08:00:00Z"),
                readAt
        );
    }
}
