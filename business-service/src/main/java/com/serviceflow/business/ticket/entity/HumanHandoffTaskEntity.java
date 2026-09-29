package com.serviceflow.business.ticket.entity;

import java.time.Instant;
import java.util.UUID;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import com.serviceflow.business.ticket.enums.HumanHandoffTaskStatus;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("human_handoff_task")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class HumanHandoffTaskEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private UUID requestId;
    private String requesterReference;
    private String handoffReason;
    private HumanHandoffTaskStatus status;
    private String assignedTo;
    private Instant createdAt;
    private Instant claimedAt;
    private Instant resolvedAt;
    @Version
    private Long version;
}
