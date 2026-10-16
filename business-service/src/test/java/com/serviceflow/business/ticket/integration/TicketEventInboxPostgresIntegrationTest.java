package com.serviceflow.business.ticket.integration;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.serviceflow.business.ServiceFlowBusinessApplication;
import com.serviceflow.business.ticket.dao.entity.TicketEventInboxEntity;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketEventInboxMessage;
import com.serviceflow.business.ticket.manager.mq.inbox.TicketEventInboxService;
import com.serviceflow.business.ticket.dao.mapper.TicketEventInboxMapper;

/** Opt-in real PostgreSQL test for V8 and ON CONFLICT idempotency. */
@SpringBootTest(
        classes = ServiceFlowBusinessApplication.class,
        properties = {
                "spring.autoconfigure.exclude=",
                "eduops.outbox.delivery.enabled=false",
                "eduops.outbox.inbox.enabled=false"
        }
)
@ActiveProfiles("local")
@Transactional
@EnabledIfSystemProperty(
        named = "runPostgresInboxIntegrationTests",
        matches = "true"
)
class TicketEventInboxPostgresIntegrationTest {

    @Autowired
    private TicketEventInboxService inboxService;

    @Autowired
    private TicketEventInboxMapper inboxMapper;

    @Test
    void stores_one_row_when_the_same_event_is_delivered_twice() {
        UUID eventId = UUID.randomUUID();
        TicketEventInboxMessage message = new TicketEventInboxMessage(
                eventId,
                "ticket.status_changed.v1",
                "ticket",
                UUID.randomUUID(),
                "{\"status\":\"RESOLVED\"}"
        );

        var first = inboxService.recordIfFirstSeen(message);
        var redelivery = inboxService.recordIfFirstSeen(message);

        Long rowCount = inboxMapper.selectCount(
                Wrappers.<TicketEventInboxEntity>lambdaQuery()
                        .eq(TicketEventInboxEntity::getEventId, eventId)
        );

        assertThat(first.created()).isTrue();
        assertThat(redelivery.created()).isFalse();
        assertThat(rowCount).isEqualTo(1L);
    }
}
