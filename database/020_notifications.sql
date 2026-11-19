CREATE TABLE campus_notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id uuid NOT NULL REFERENCES accounts (id),
    event_key text NOT NULL CHECK (length(event_key) BETWEEN 1 AND 200),
    kind text NOT NULL CHECK (kind IN (
        'workshop_rescheduled', 'workshop_cancelled', 'evidence_submitted',
        'evidence_approved', 'evidence_returned', 'redemption_requested',
        'redemption_approved', 'redemption_rejected'
    )),
    workshop_id uuid REFERENCES workshops (id),
    course_id uuid REFERENCES course_sections (id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    read_at timestamptz,
    CHECK ((workshop_id IS NOT NULL) <> (course_id IS NOT NULL)),
    CHECK ((kind IN ('redemption_requested', 'redemption_approved', 'redemption_rejected')) = (course_id IS NOT NULL)),
    UNIQUE (account_id, event_key)
);

CREATE INDEX campus_notifications_history ON campus_notifications (account_id, created_at DESC, id DESC);
CREATE INDEX campus_notifications_unread ON campus_notifications (account_id, created_at DESC, id DESC)
    WHERE read_at IS NULL;
