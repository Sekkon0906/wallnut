ALTER TABLE workshops
    ADD COLUMN cancelled_at timestamptz,
    ADD COLUMN schedule_revision integer NOT NULL DEFAULT 1 CHECK (schedule_revision >= 1),
    ADD CONSTRAINT cancelled_workshop_before_start CHECK (
        cancelled_at IS NULL OR
        (cancelled_at < starts_at AND attendance_code_hash IS NULL AND attendance_code_expires_at IS NULL)
    );

CREATE TABLE workshop_agenda_changes (
    workshop_id uuid NOT NULL REFERENCES workshops (id),
    revision integer NOT NULL CHECK (revision > 1),
    request_id uuid NOT NULL,
    actor_id uuid NOT NULL REFERENCES accounts (id),
    kind text NOT NULL CHECK (kind IN ('rescheduled', 'cancelled')),
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 3 AND 280),
    previous_schedule jsonb NOT NULL,
    payload jsonb NOT NULL,
    changed_at timestamptz NOT NULL,
    PRIMARY KEY (workshop_id, revision),
    UNIQUE (workshop_id, request_id)
);
