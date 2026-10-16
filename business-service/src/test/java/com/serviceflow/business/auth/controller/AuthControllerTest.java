package com.serviceflow.business.auth.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.serviceflow.business.ticket.dao.mapper.TicketMapper;
import com.serviceflow.business.ticket.dao.mapper.HumanHandoffTaskMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.auth.dao.mapper.AccountUserMapper;

@SpringBootTest
@AutoConfigureMockMvc
class AuthControllerTest {

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
    private TicketEventInboxMapper ticketEventInboxMapper;

    @MockitoBean
    private TicketNotificationMapper ticketNotificationMapper;

    @Test
    void issues_a_bearer_token_after_valid_credentials() throws Exception {
        mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "username": "support",
                                  "password": "support-pass"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.tokenType").value("Bearer"))
                .andExpect(jsonPath("$.data.accessToken").isNotEmpty())
                .andExpect(jsonPath("$.data.expiresAt").isNotEmpty());
    }

    @Test
    void rejects_invalid_login_credentials_without_disclosing_which_field_failed()
            throws Exception {
        mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "username": "support",
                                  "password": "wrong-password"
                                }
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401))
                .andExpect(jsonPath("$.message")
                        .value("invalid username or password"));
    }

    @Test
    void rejects_a_blank_username_before_authentication() throws Exception {
        mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "username": " ",
                                  "password": "support-pass"
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message")
                        .value("username must not be blank"));
    }
}
