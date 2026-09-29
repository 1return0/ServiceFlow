package com.serviceflow.business.ticket.mapper;

import java.time.Instant;
import java.util.UUID;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.serviceflow.business.ticket.entity.HumanHandoffTaskEntity;

@Mapper
public interface HumanHandoffTaskMapper extends BaseMapper<HumanHandoffTaskEntity> {
    int claimPending(@Param("taskId") UUID taskId, @Param("assignee") String assignee, @Param("claimedAt") Instant claimedAt);
    int resolveClaimed(@Param("taskId") UUID taskId, @Param("assignee") String assignee, @Param("resolvedAt") Instant resolvedAt);
}
