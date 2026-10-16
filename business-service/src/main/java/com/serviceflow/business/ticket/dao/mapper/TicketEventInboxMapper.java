package com.serviceflow.business.ticket.dao.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.serviceflow.business.ticket.dao.entity.TicketEventInboxEntity;

@Mapper
public interface TicketEventInboxMapper extends BaseMapper<TicketEventInboxEntity> {

    /** PostgreSQL keeps the transaction usable when the event was already received. */
    int insertIfAbsent(TicketEventInboxEntity entity);
}
