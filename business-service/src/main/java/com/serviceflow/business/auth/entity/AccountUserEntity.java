package com.serviceflow.business.auth.entity;

import java.time.Instant;
import java.util.UUID;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/** Persistent account data used by authentication; passwords are stored only as hashes. */
@TableName("account_user")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class AccountUserEntity {

    @TableId(type = IdType.INPUT)
    private UUID id;
    private String username;
    private String passwordHash;
    private String roleCode;
    private Boolean enabled;
    private Instant createdAt;
    private Instant updatedAt;

    @Version
    private Long version;
}
