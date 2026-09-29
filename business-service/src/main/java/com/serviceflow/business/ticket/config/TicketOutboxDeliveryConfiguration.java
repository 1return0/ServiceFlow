package com.serviceflow.business.ticket.config;

import java.time.Clock;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

import com.serviceflow.business.ticket.mapper.TicketOutboxEventMapper;
import com.serviceflow.business.ticket.outbox.TicketOutboxDeliveryScheduler;
import com.serviceflow.business.ticket.outbox.TicketOutboxDeliveryService;
import com.serviceflow.business.ticket.outbox.TicketOutboxEventPublisher;

@Configuration
@EnableScheduling
@ConditionalOnProperty(
        prefix = "eduops.outbox.delivery",
        name = "enabled",
        havingValue = "true"
)
public class TicketOutboxDeliveryConfiguration {

    @Bean
    TicketOutboxDeliveryService ticketOutboxDeliveryService(
            TicketOutboxEventMapper eventMapper,
            TicketOutboxEventPublisher publisher
    ) {
        return new TicketOutboxDeliveryService(eventMapper, publisher, Clock.systemUTC());
    }

    @Bean
    @ConditionalOnProperty(
            prefix = "eduops.outbox.delivery",
            name = "scheduler-enabled",
            havingValue = "true"
    )
    TicketOutboxDeliveryScheduler ticketOutboxDeliveryScheduler(
            TicketOutboxDeliveryService deliveryService,
            @Value("${eduops.outbox.delivery.batch-size:20}") int batchSize
    ) {
        return new TicketOutboxDeliveryScheduler(deliveryService, batchSize);
    }
}
