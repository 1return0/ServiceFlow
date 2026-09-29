ALTER TABLE ticket
    ADD COLUMN assignee_reference VARCHAR(64),
    ADD COLUMN claimed_at TIMESTAMPTZ;

CREATE INDEX idx_ticket_status_assignee_submitted
    ON ticket (status, assignee_reference, submitted_at DESC, id DESC);
