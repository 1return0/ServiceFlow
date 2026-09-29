package com.serviceflow.business.ticket.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.security.test.context.support.WithMockUser;

import com.serviceflow.business.ticket.entity.TicketEntity;
import com.serviceflow.business.ticket.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.enums.ServiceRequestCategory;
import com.serviceflow.business.ticket.enums.TicketStatus;
import com.serviceflow.business.ticket.mapper.HumanHandoffTaskMapper;
import com.serviceflow.business.ticket.mapper.TicketMapper;
import com.serviceflow.business.ticket.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.auth.mapper.AccountUserMapper;

@SpringBootTest
@AutoConfigureMockMvc
@WithMockUser(roles = "STUDENT")
class TicketControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TicketMapper ticketMapper;

    @MockitoBean
    private HumanHandoffTaskMapper humanHandoffTaskMapper;

    @MockitoBean
    private AccountUserMapper accountUserMapper;

    @MockitoBean
    private TicketOutboxEventMapper ticketOutboxEventMapper;

    @MockitoBean
    private TicketNotificationMapper ticketNotificationMapper;

    @MockitoBean
    private TicketEventInboxMapper ticketEventInboxMapper;

    @BeforeEach
    void setUp() {
        when(ticketMapper.insert(any(TicketEntity.class))).thenReturn(1);
        when(ticketMapper.updateById(any(TicketEntity.class))).thenReturn(1);
        when(ticketOutboxEventMapper.insert(any(TicketOutboxEventEntity.class))).thenReturn(1);
    }

    @Test
    @WithMockUser(username = "stu-demo-001", roles = "STUDENT")
    void creates_a_synthetic_campus_network_ticket() throws Exception {
        mockMvc.perform(post("/api/v1/tickets")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("X-Actor-Role", "SUPPORT_AGENT")
                        .content("""
                                {
                                  "category": "CAMPUS_NETWORK",
                                  "summary": "  VPN cannot connect  "
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.data.requesterReference").value("stu-demo-001"))
                .andExpect(jsonPath("$.data.summary").value("VPN cannot connect"))
                .andExpect(jsonPath("$.data.status").value("OPEN"));
    }

    @Test
    void rejects_a_blank_summary_before_calling_the_service() throws Exception {
        mockMvc.perform(post("/api/v1/tickets")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("X-Actor-Role", "SUPPORT_AGENT")
                        .content("""
                                {
                                  "category": "CAMPUS_NETWORK",
                                  "summary": "   "
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    @WithMockUser(username = "stu-smoke-001", roles = "STUDENT")
    void returns_a_ticket_to_its_student_requester() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");
        when(ticketMapper.selectById(ticketId)).thenReturn(new TicketEntity(
                ticketId,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        ));

        mockMvc.perform(get("/api/v1/tickets/{ticketId}", ticketId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.id").value(ticketId.toString()))
                .andExpect(jsonPath("$.data.status").value("OPEN"));
    }

    @Test
    @WithMockUser(username = "other-student", roles = "STUDENT")
    void hides_another_students_ticket_as_not_found() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");
        when(ticketMapper.selectById(ticketId)).thenReturn(new TicketEntity(
                ticketId,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        ));

        mockMvc.perform(get("/api/v1/tickets/{ticketId}", ticketId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    @WithMockUser(username = "support", roles = "SUPPORT_AGENT")
    void allows_support_agent_to_read_a_students_ticket() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");
        when(ticketMapper.selectById(ticketId)).thenReturn(new TicketEntity(
                ticketId,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        ));

        mockMvc.perform(get("/api/v1/tickets/{ticketId}", ticketId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.requesterReference").value("stu-smoke-001"));
    }

    @Test
    @WithMockUser(username = "admin", roles = "ADMIN")
    void allows_admin_to_read_a_students_ticket() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");
        when(ticketMapper.selectById(ticketId)).thenReturn(new TicketEntity(
                ticketId,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        ));

        mockMvc.perform(get("/api/v1/tickets/{ticketId}", ticketId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.requesterReference").value("stu-smoke-001"));
    }

    @Test
    void returns_404_when_a_ticket_does_not_exist() throws Exception {
        UUID ticketId = UUID.fromString("a87f2e4f-0fbd-4b57-b7fe-d24884650850");
        when(ticketMapper.selectById(ticketId)).thenReturn(null);

        mockMvc.perform(get("/api/v1/tickets/{ticketId}", ticketId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    void returns_400_when_ticket_id_is_not_a_uuid() throws Exception {
        mockMvc.perform(get("/api/v1/tickets/abc"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("invalid value for parameter: ticketId"))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    @WithMockUser(roles = "SUPPORT_AGENT")
    void transitions_an_open_ticket_to_in_progress() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");
        TicketEntity assignedTicket = new TicketEntity(
                ticketId,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        );
        assignedTicket.setAssigneeReference("user");
        when(ticketMapper.selectById(ticketId)).thenReturn(assignedTicket);

        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", ticketId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("X-Actor-Role", "SUPPORT_AGENT")
                        .content("""
                                {"targetStatus": "IN_PROGRESS"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.status").value("IN_PROGRESS"));
    }

    @Test
    @WithMockUser(roles = "SUPPORT_AGENT")
    void rejects_skipping_from_open_to_closed() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");
        TicketEntity assignedTicket = new TicketEntity(
                ticketId,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        );
        assignedTicket.setAssigneeReference("user");
        when(ticketMapper.selectById(ticketId)).thenReturn(assignedTicket);

        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", ticketId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("X-Actor-Role", "SUPPORT_AGENT")
                        .content("""
                                {"targetStatus": "CLOSED"}
                                """))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value(409))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    void forbids_a_student_from_updating_ticket_status() throws Exception {
        UUID ticketId = UUID.fromString("24e34aa1-6847-4673-8152-1f81c17769c4");

        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", ticketId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("X-Actor-Role", "STUDENT")
                        .content("""
                                {"targetStatus": "IN_PROGRESS"}
                                """))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403))
                .andExpect(jsonPath("$.data").doesNotExist());
    }
}
