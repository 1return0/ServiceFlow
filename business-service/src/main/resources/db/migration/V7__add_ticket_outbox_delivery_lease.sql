ALTER TABLE ticket_outbox_event
    ADD COLUMN lease_token UUID NULL,
    ADD COLUMN lease_expires_at TIMESTAMPTZ NULL;

CREATE INDEX idx_ticket_outbox_event_delivery_lease
    ON ticket_outbox_event (published_at, lease_expires_at, created_at);
