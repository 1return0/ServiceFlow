package com.serviceflow.business.ticket.dao.mapper;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.serviceflow.business.ticket.dao.entity.TicketOutboxEventEntity;

@Mapper
public interface TicketOutboxEventMapper extends BaseMapper<TicketOutboxEventEntity> {

    List<TicketOutboxEventEntity> claimNextUnpublished(
            @Param("limit") int limit,
            @Param("now") Instant now,
            @Param("leaseToken") UUID leaseToken,
            @Param("leaseExpiresAt") Instant leaseExpiresAt
    );

    TicketOutboxEventEntity claimById(
            @Param("eventId") UUID eventId,
            @Param("now") Instant now,
            @Param("leaseToken") UUID leaseToken,
            @Param("leaseExpiresAt") Instant leaseExpiresAt
    );

    int markPublished(
            @Param("eventId") UUID eventId,
            @Param("leaseToken") UUID leaseToken,
            @Param("publishedAt") Instant publishedAt
    );

    int releaseAfterFailure(
            @Param("eventId") UUID eventId,
            @Param("leaseToken") UUID leaseToken,
            @Param("errorCode") String errorCode
    );
}
