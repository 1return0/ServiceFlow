CREATE TABLE ticket_event_inbox (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_ticket_event_inbox_received_at
    ON ticket_event_inbox (received_at DESC);
