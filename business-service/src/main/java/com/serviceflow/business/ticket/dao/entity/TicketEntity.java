package com.serviceflow.business.ticket.dao.entity;

import java.time.Instant;
import java.util.UUID;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import com.serviceflow.business.ticket.domain.ServiceRequestCategory;
import com.serviceflow.business.ticket.domain.TicketStatus;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Current ticket business object. It will become the MyBatis persistence entity after
 * the database module is introduced; it has no database annotation in the bootstrap stage.
 */
@TableName("ticket")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class TicketEntity {

    @TableId(type = IdType.INPUT)
    private UUID id;
    private String requesterReference;
    private ServiceRequestCategory category;
    private String summary;
    private Instant submittedAt;
    private TicketStatus status;
    private String assigneeReference;
    private Instant claimedAt;

    @Version
    private Long version;

    public TicketEntity(
            UUID id,
            String requesterReference,
            ServiceRequestCategory category,
            String summary,
            Instant submittedAt,
            TicketStatus status
    ) {
        this(id, requesterReference, category, summary, submittedAt, status, null);
    }

    public TicketEntity(
            UUID id, String requesterReference, ServiceRequestCategory category,
            String summary, Instant submittedAt, TicketStatus status, Long version
    ) {
        this(id, requesterReference, category, summary, submittedAt, status, null, null, version);
    }

}
