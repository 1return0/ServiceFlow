package com.serviceflow.business.ticket.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.serviceflow.business.ticket.entity.TicketNotificationEntity;
import com.serviceflow.business.ticket.mapper.HumanHandoffTaskMapper;
import com.serviceflow.business.ticket.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.mapper.TicketMapper;
import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.auth.mapper.AccountUserMapper;

@SpringBootTest
@AutoConfigureMockMvc
class TicketNotificationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TicketNotificationMapper notificationMapper;

    @MockitoBean
    private HumanHandoffTaskMapper humanHandoffTaskMapper;

    @MockitoBean
    private AccountUserMapper accountUserMapper;

    @MockitoBean
    private TicketMapper ticketMapper;

    @MockitoBean
    private TicketOutboxEventMapper ticketOutboxEventMapper;

    @MockitoBean
    private TicketEventInboxMapper ticketEventInboxMapper;

    @Test
    @WithMockUser(username = "student", roles = "STUDENT")
    void lists_only_the_authenticated_students_notifications() throws Exception {
        UUID notificationId = UUID.fromString("f83b4629-e0e4-4b3b-9cbe-bf5ccde20c66");
        when(notificationMapper.selectRecentByRecipient("student", 20)).thenReturn(List.of(
                notification(notificationId, "student", null)
        ));

        mockMvc.perform(get("/api/v1/notifications/me"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data[0].id").value(notificationId.toString()));

        verify(notificationMapper).selectRecentByRecipient("student", 20);
    }

    @Test
    void rejects_an_anonymous_notification_request() throws Exception {
        mockMvc.perform(get("/api/v1/notifications/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "support", roles = "SUPPORT_AGENT")
    void rejects_a_non_student_notification_request() throws Exception {
        mockMvc.perform(get("/api/v1/notifications/me"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }

    @Test
    @WithMockUser(username = "student", roles = "STUDENT")
    void hides_another_students_notification_as_not_found() throws Exception {
        UUID notificationId = UUID.fromString("63e7d79d-b6f6-4a8f-b487-b27b0cf4c59d");
        when(notificationMapper.selectByIdAndRecipient(notificationId, "student"))
                .thenReturn(null);

        mockMvc.perform(patch("/api/v1/notifications/{notificationId}/read", notificationId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404));

        verify(notificationMapper, never()).markReadIfUnread(
                any(UUID.class), any(String.class), any(Instant.class)
        );
    }

    @Test
    @WithMockUser(username = "student", roles = "STUDENT")
    void marks_the_students_own_notification_as_read() throws Exception {
        UUID notificationId = UUID.fromString("46bce8f7-2f1b-4cee-b4ad-7b0a127a9073");
        TicketNotificationEntity entity = notification(notificationId, "student", null);
        when(notificationMapper.selectByIdAndRecipient(notificationId, "student"))
                .thenReturn(entity);
        when(notificationMapper.markReadIfUnread(eq(notificationId), eq("student"), any(Instant.class)))
                .thenReturn(1);

        mockMvc.perform(patch("/api/v1/notifications/{notificationId}/read", notificationId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.readAt").isNotEmpty());
    }

    private static TicketNotificationEntity notification(
            UUID notificationId,
            String recipientReference,
            Instant readAt
    ) {
        return new TicketNotificationEntity(
                notificationId,
                UUID.randomUUID(),
                recipientReference,
                UUID.randomUUID(),
                "ticket.status_changed.v1",
                "Your service ticket status is now RESOLVED.",
                Instant.parse("2026-09-18T08:00:00Z"),
                readAt
        );
    }
}
