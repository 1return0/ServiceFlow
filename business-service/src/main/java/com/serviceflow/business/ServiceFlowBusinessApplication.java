package com.serviceflow.business;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.mybatis.spring.annotation.MapperScan;

@SpringBootApplication
@MapperScan({
        "com.serviceflow.business.auth.mapper",
        "com.serviceflow.business.ticket.mapper"
})
public class ServiceFlowBusinessApplication {

    public static void main(String[] args) {
        SpringApplication.run(ServiceFlowBusinessApplication.class, args);
    }
}
