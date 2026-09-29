package com.serviceflow.business.common.mybatis;

import java.util.UUID;

import com.baomidou.mybatisplus.autoconfigure.ConfigurationCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MybatisTypeHandlerConfig {

    @Bean
    public ConfigurationCustomizer postgreSqlUuidTypeHandlerCustomizer() {
        return configuration -> configuration.getTypeHandlerRegistry().register(
                UUID.class,
                PostgreSqlUuidTypeHandler.class
        );
    }
}
