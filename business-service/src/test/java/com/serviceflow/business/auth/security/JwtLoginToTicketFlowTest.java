package com.serviceflow.business.auth.security;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

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
class JwtLoginToTicketFlowTest {

    private static final UUID TICKET_ID = UUID.fromString(
            "24e34aa1-6847-4673-8152-1f81c17769c4"
    );

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private TicketMapper ticketMapper;

    @MockitoBean
    private HumanHandoffTaskMapper humanHandoffTaskMapper;

    @MockitoBean
    private AccountUserMapper accountUserMapper;

    @MockitoBean
    private TicketOutboxEventMapper ticketOutboxEventMapper;

    @MockitoBean
    private TicketEventInboxMapper ticketEventInboxMapper;

    @MockitoBean
    private TicketNotificationMapper ticketNotificationMapper;

    @BeforeEach
    void setUp() {
        TicketEntity assignedTicket = new TicketEntity(
                TICKET_ID,
                "stu-smoke-001",
                ServiceRequestCategory.CAMPUS_NETWORK,
                "VPN cannot connect",
                Instant.parse("2026-08-28T11:43:19Z"),
                TicketStatus.OPEN
        );
        assignedTicket.setAssigneeReference("support");
        when(ticketMapper.selectById(TICKET_ID)).thenReturn(assignedTicket);
        when(ticketMapper.updateById(any(TicketEntity.class))).thenReturn(1);
        when(ticketOutboxEventMapper.insert(any(TicketOutboxEventEntity.class)))
                .thenReturn(1);
    }

    @Test
    void logs_in_then_uses_the_returned_bearer_token_for_a_protected_ticket_api()
            throws Exception {
        MvcResult loginResult = mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username": "support", "password": "support-pass"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.tokenType").value("Bearer"))
                .andReturn();
        JsonNode responseBody = objectMapper.readTree(
                loginResult.getResponse().getContentAsString()
        );
        String accessToken = responseBody.path("data").path("accessToken").asText();

        mockMvc.perform(get("/api/v1/auth/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.subject").value("support"))
                .andExpect(jsonPath("$.data.roles[0]").value("SUPPORT_AGENT"));

        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", TICKET_ID)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetStatus": "IN_PROGRESS"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.status").value("IN_PROGRESS"));
    }
}
