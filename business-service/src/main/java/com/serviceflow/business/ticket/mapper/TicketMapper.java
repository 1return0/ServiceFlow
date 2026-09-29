package com.serviceflow.business.ticket.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.serviceflow.business.ticket.entity.TicketEntity;

@Mapper
public interface TicketMapper extends BaseMapper<TicketEntity> {

    @Select("""
            SELECT id, requester_reference, category, summary, submitted_at, status, version
            FROM ticket WHERE requester_reference = #{requesterReference}
            ORDER BY submitted_at DESC, id DESC LIMIT #{limit} OFFSET #{offset}
            """)
    List<TicketEntity> selectPageByRequester(@Param("requesterReference") String requesterReference,
                                              @Param("limit") long limit, @Param("offset") long offset);

    @Select("SELECT COUNT(*) FROM ticket WHERE requester_reference = #{requesterReference}")
    long countByRequester(@Param("requesterReference") String requesterReference);

    @Update("UPDATE ticket SET assignee_reference=#{operator}, claimed_at=#{claimedAt} "
            + "WHERE id=#{ticketId} AND status='OPEN' AND assignee_reference IS NULL")
    int claimOpenTicket(@Param("ticketId") java.util.UUID ticketId, @Param("operator") String operator,
                        @Param("claimedAt") java.time.Instant claimedAt);
}
