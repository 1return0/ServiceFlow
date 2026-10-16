package com.serviceflow.business.auth.dao.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.serviceflow.business.auth.dao.entity.AccountUserEntity;

@Mapper
public interface AccountUserMapper extends BaseMapper<AccountUserEntity> {
}
