package com.serviceflow.business.auth.security;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;

import com.serviceflow.business.auth.service.JwtTokenService;
import com.serviceflow.business.auth.service.IssuedJwt;
import com.serviceflow.business.auth.dao.mapper.AccountUserMapper;
import com.serviceflow.business.ticket.dao.entity.TicketEntity;
import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.domain.ServiceRequestCategory;
import com.serviceflow.business.ticket.domain.TicketStatus;
import com.serviceflow.business.ticket.dao.mapper.HumanHandoffTaskMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;

@SpringBootTest
@AutoConfigureMockMvc
class JwtAuthenticationFilterTest {

    private static final UUID TICKET_ID = UUID.fromString(
            "24e34aa1-6847-4673-8152-1f81c17769c4"
    );

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtTokenService jwtTokenService;

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
    void allows_a_support_bearer_token_to_update_ticket_status() throws Exception {
        String token = issueToken("support", "ROLE_SUPPORT_AGENT");

        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", TICKET_ID)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetStatus": "IN_PROGRESS"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.status").value("IN_PROGRESS"));
    }

    @Test
    void rejects_a_tampered_bearer_token_before_controller_execution()
            throws Exception {
        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", TICKET_ID)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer tampered.token.value")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetStatus": "IN_PROGRESS"}
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401))
                .andExpect(jsonPath("$.message")
                        .value("invalid or expired Bearer token"));
    }

    @Test
    void authenticates_student_but_forbids_status_update() throws Exception {
        String token = issueToken("student", "ROLE_STUDENT");

        mockMvc.perform(patch("/api/v1/tickets/{ticketId}/status", TICKET_ID)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetStatus": "IN_PROGRESS"}
                                """))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }

    private String issueToken(String username, String role) {
        IssuedJwt issuedJwt = jwtTokenService.issue(
                UsernamePasswordAuthenticationToken.authenticated(
                        username,
                        null,
                        List.of(new SimpleGrantedAuthority(role))
                )
        );
        return issuedJwt.token();
    }
}
