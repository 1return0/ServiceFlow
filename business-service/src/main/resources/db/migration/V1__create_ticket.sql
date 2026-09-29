CREATE TABLE ticket (
    id UUID PRIMARY KEY,
    requester_reference VARCHAR(64) NOT NULL,
    category VARCHAR(64) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ticket_status_submitted_at
    ON ticket (status, submitted_at DESC);
