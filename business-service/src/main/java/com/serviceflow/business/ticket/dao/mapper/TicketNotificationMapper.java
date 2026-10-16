package com.serviceflow.business.ticket.dao.mapper;

import java.util.List;
import java.time.Instant;
import java.util.UUID;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.serviceflow.business.ticket.dao.entity.TicketNotificationEntity;

@Mapper
public interface TicketNotificationMapper extends BaseMapper<TicketNotificationEntity> {

    List<TicketNotificationEntity> selectRecentByRecipient(
            @Param("recipientReference") String recipientReference,
            @Param("limit") int limit
    );

    TicketNotificationEntity selectByIdAndRecipient(
            @Param("notificationId") UUID notificationId,
            @Param("recipientReference") String recipientReference
    );

    /** Atomic compare-and-set: a second read action leaves the existing timestamp intact. */
    int markReadIfUnread(
            @Param("notificationId") UUID notificationId,
            @Param("recipientReference") String recipientReference,
            @Param("readAt") Instant readAt
    );

    long countUnreadByRecipient(@Param("recipientReference") String recipientReference);
}
