package com.serviceflow.business.ticket.manager.mq.inbox;

/** created=false means a redelivery of an event that was already durably received. */
public record TicketEventInboxRecordResult(boolean created) {

    public static TicketEventInboxRecordResult firstDeliveryRecorded() {
        return new TicketEventInboxRecordResult(true);
    }

    public static TicketEventInboxRecordResult alreadyProcessed() {
        return new TicketEventInboxRecordResult(false);
    }
}
