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

/** One durable consumer-side receipt per integration event. */
@TableName("ticket_event_inbox")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class TicketEventInboxEntity {

    @TableId(value = "event_id", type = IdType.INPUT)
    private UUID eventId;
    private String eventType;
    private String aggregateType;
    private UUID aggregateId;

    @TableField(typeHandler = JsonbStringTypeHandler.class)
    private String payload;

    private Instant receivedAt;
}
