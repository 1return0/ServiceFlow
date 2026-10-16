package com.serviceflow.business.api;

import static org.hamcrest.Matchers.hasItem;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.serviceflow.business.ticket.dao.mapper.TicketMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;
import com.serviceflow.business.ticket.dao.mapper.HumanHandoffTaskMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketNotificationMapper;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.auth.dao.mapper.AccountUserMapper;

@SpringBootTest
@AutoConfigureMockMvc
class SystemControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TicketMapper ticketMapper;

    @MockitoBean
    private HumanHandoffTaskMapper humanHandoffTaskMapper;

    @MockitoBean
    private AccountUserMapper accountUserMapper;

    /**
     * This is a web-context test: persistence adapters are replaced with mocks.
     * Real PostgreSQL/Flyway coverage remains in explicitly enabled integration tests.
     */
    @MockitoBean
    private TicketOutboxEventMapper ticketOutboxEventMapper;

    @MockitoBean
    private TicketEventInboxMapper ticketEventInboxMapper;

    @MockitoBean
    private TicketNotificationMapper ticketNotificationMapper;

    @Test
    void healthReturnsStableServiceIdentity() throws Exception {
        mockMvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.service").value("eduops-business"));
    }

    @Test
    void metadataMakesLlmBoundaryExplicit() throws Exception {
        mockMvc.perform(get("/api/v1/meta"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.authoritativeResponsibilities", hasItem("priority-and-sla-calculation")))
                .andExpect(jsonPath("$.prohibitedDelegations", hasItem("llm-authorized-writes")))
                .andExpect(jsonPath("$.syntheticDataOnly").value(true));
    }
}
