package com.serviceflow.business.ticket.manager.mq.outbox;

import java.time.Clock;
import java.time.Instant;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;
import com.serviceflow.business.ticket.dao.mapper.TicketOutboxEventMapper;

/** Read-only operational queries for diagnosing the durable Outbox backlog. */
@Service
public class TicketOutboxMonitoringService {

    private final TicketOutboxEventMapper eventMapper;
    private final Clock clock;

    @Autowired
    public TicketOutboxMonitoringService(TicketOutboxEventMapper eventMapper) {
        this(eventMapper, Clock.systemUTC());
    }

    TicketOutboxMonitoringService(TicketOutboxEventMapper eventMapper, Clock clock) {
        this.eventMapper = eventMapper;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public TicketOutboxDeliverySummary getDeliverySummary() {
        Instant now = clock.instant();
        long pendingEvents = eventMapper.selectCount(
                Wrappers.<TicketOutboxEventEntity>lambdaQuery()
                        .isNull(TicketOutboxEventEntity::getPublishedAt)
        );
        long activelyLeasedEvents = eventMapper.selectCount(
                Wrappers.<TicketOutboxEventEntity>lambdaQuery()
                        .isNull(TicketOutboxEventEntity::getPublishedAt)
                        .gt(TicketOutboxEventEntity::getLeaseExpiresAt, now)
        );
        long retryableFailedEvents = eventMapper.selectCount(
                Wrappers.<TicketOutboxEventEntity>lambdaQuery()
                        .isNull(TicketOutboxEventEntity::getPublishedAt)
                        .isNotNull(TicketOutboxEventEntity::getLastError)
        );
        TicketOutboxEventEntity oldestPending = eventMapper.selectOne(
                Wrappers.<TicketOutboxEventEntity>lambdaQuery()
                        .isNull(TicketOutboxEventEntity::getPublishedAt)
                        .orderByAsc(TicketOutboxEventEntity::getCreatedAt)
                        .last("LIMIT 1")
        );
        return new TicketOutboxDeliverySummary(
                pendingEvents,
                activelyLeasedEvents,
                retryableFailedEvents,
                oldestPending == null ? null : oldestPending.getCreatedAt()
        );
    }
}
