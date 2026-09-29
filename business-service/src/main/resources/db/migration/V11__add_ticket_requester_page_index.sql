CREATE INDEX idx_ticket_requester_submitted_id
    ON ticket (requester_reference, submitted_at DESC, id DESC);
