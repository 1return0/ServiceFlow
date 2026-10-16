package com.serviceflow.business.ticket.dao.entity;

import java.time.Instant;
import java.util.UUID;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.serviceflow.business.common.mybatis.JsonbStringTypeHandler;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("ticket_outbox_event")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class TicketOutboxEventEntity {

    @TableId(type = IdType.INPUT)
    private UUID id;
    private String aggregateType;
    private UUID aggregateId;
    private String eventType;

    @TableField(typeHandler = JsonbStringTypeHandler.class)
    private String payload;

    private Instant createdAt;
    private Instant publishedAt;
    private Integer publishAttempts;
    private String lastError;
    private UUID leaseToken;
    private Instant leaseExpiresAt;
}
