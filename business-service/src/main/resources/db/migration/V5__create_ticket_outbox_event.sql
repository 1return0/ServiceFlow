CREATE TABLE ticket_outbox_event (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ NULL,
    publish_attempts INTEGER NOT NULL DEFAULT 0,
    last_error VARCHAR(500) NULL
);

CREATE INDEX idx_ticket_outbox_event_unpublished
    ON ticket_outbox_event (created_at ASC)
    WHERE published_at IS NULL;
