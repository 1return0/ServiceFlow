package com.serviceflow.business.ticket.entity;

import java.time.Instant;
import java.util.UUID;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/** One student-visible notification derived from a successfully consumed event. */
@TableName("ticket_notification")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class TicketNotificationEntity {

    @TableId(type = IdType.INPUT)
    private UUID id;
    private UUID eventId;
    private String recipientReference;
    private UUID ticketId;
    private String notificationType;
    private String message;
    private Instant createdAt;
    private Instant readAt;
}
