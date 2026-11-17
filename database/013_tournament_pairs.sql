ALTER TABLE campus_events
    ADD COLUMN tournament_format text NOT NULL DEFAULT 'individual',
    ADD CONSTRAINT campus_events_tournament_format CHECK (
        tournament_format = 'individual'
        OR (tournament_format = 'doubles' AND category = 'tournament'
            AND capacity >= 4 AND capacity % 2 = 0)
    );

CREATE TABLE tournament_pairs (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES campus_events (id),
    inviter_id uuid NOT NULL,
    invitee_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    accepted_at timestamptz,
    UNIQUE (event_id, inviter_id),
    CHECK (inviter_id <> invitee_id),
    FOREIGN KEY (event_id, inviter_id) REFERENCES campus_event_enrollments (event_id, student_id)
        ON DELETE CASCADE,
    FOREIGN KEY (event_id, invitee_id) REFERENCES campus_event_enrollments (event_id, student_id)
        ON DELETE CASCADE
);

CREATE INDEX tournament_pairs_by_invitee ON tournament_pairs (event_id, invitee_id);

ALTER TABLE tournament_participants
    ADD COLUMN partner_id uuid,
    ADD FOREIGN KEY (event_id, partner_id) REFERENCES campus_event_enrollments (event_id, student_id),
    ADD CHECK (student_id <> partner_id);
