CREATE TABLE human_handoff_task (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL UNIQUE,
    requester_reference VARCHAR(64) NOT NULL,
    handoff_reason VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    assigned_to VARCHAR(64) NULL,
    created_at TIMESTAMPTZ NOT NULL,
    claimed_at TIMESTAMPTZ NULL,
    resolved_at TIMESTAMPTZ NULL,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_human_handoff_task_status
        CHECK (status IN ('PENDING', 'CLAIMED', 'RESOLVED')),
    CONSTRAINT chk_human_handoff_task_reason
        CHECK (handoff_reason IN ('account_security_risk', 'physical_safety_risk'))
);

CREATE INDEX idx_human_handoff_task_status_created_at
    ON human_handoff_task (status, created_at DESC);
