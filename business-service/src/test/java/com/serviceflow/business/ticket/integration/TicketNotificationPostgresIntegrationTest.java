package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.ticket.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.notification.TicketNotificationQueryService;

/**
 * Opt-in PostgreSQL smoke for notification ownership, unread counting and
 * idempotent read acknowledgement. The test transaction rolls its fixture back.
 */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = "spring.autoconfigure.exclude="
)
@ActiveProfiles("local")
@Transactional
@EnabledIfEnvironmentVariable(
        named = "RUN_POSTGRES_INTEGRATION_TESTS",
        matches = "true"
)
class TicketNotificationPostgresIntegrationTest {

    @Autowired
    private TicketNotificationMapper notificationMapper;

    @Autowired
    private TicketNotificationQueryService notificationQueryService;

    @Test
    void reads_and_marks_only_the_owners_notification_in_real_postgresql() {
        String owner = "notification-pg-owner";
        UUID notificationId = UUID.randomUUID();
        notificationMapper.insert(new TicketNotificationEntity(
                notificationId,
                UUID.randomUUID(),
                owner,
                UUID.randomUUID(),
                "ticket.status_changed.v1",
                "PostgreSQL notification smoke",
                Instant.now(),
                null
        ));
        notificationMapper.insert(new TicketNotificationEntity(
                UUID.randomUUID(),
                UUID.randomUUID(),
                "notification-pg-other-student",
                UUID.randomUUID(),
                "ticket.status_changed.v1",
                "Other student notification",
                Instant.now(),
                null
        ));

        assertThat(notificationQueryService.listForRequester(owner, 20))
                .extracting(response -> response.id())
                .containsExactly(notificationId);
        assertThat(notificationQueryService.summarizeForRequester(owner).unreadCount())
                .isEqualTo(1L);

        var firstRead = notificationQueryService.markAsRead(owner, notificationId);
        var repeatedRead = notificationQueryService.markAsRead(owner, notificationId);

        assertThat(firstRead.readAt()).isNotNull();
        assertThat(repeatedRead.readAt()).isEqualTo(firstRead.readAt());
        assertThat(notificationQueryService.summarizeForRequester(owner).unreadCount())
                .isZero();
        assertThat(notificationMapper.selectByIdAndRecipient(
                notificationId,
                "notification-pg-other-student"
        )).isNull();
    }
}
