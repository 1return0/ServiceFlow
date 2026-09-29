CREATE TABLE ticket_notification (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    recipient_reference VARCHAR(64) NOT NULL,
    ticket_id UUID NOT NULL,
    notification_type VARCHAR(64) NOT NULL,
    message VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    read_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_ticket_notification_recipient_created_at
    ON ticket_notification (recipient_reference, created_at DESC);
