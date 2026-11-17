CREATE TABLE campus_events (
    id uuid PRIMARY KEY,
    organizer_id uuid NOT NULL REFERENCES accounts (id),
    institutional boolean NOT NULL,
    title text NOT NULL CHECK (char_length(title) BETWEEN 3 AND 100),
    description text NOT NULL CHECK (char_length(description) BETWEEN 5 AND 1200),
    category text NOT NULL CHECK (category IN ('workshop', 'tournament', 'campus')),
    location text NOT NULL CHECK (char_length(location) BETWEEN 2 AND 100),
    starts_at timestamptz NOT NULL,
    capacity integer NOT NULL CHECK (capacity BETWEEN 2 AND 500),
    cancelled boolean NOT NULL DEFAULT false
);

CREATE INDEX campus_events_schedule ON campus_events (starts_at, id);

CREATE TABLE campus_event_enrollments (
    event_id uuid NOT NULL REFERENCES campus_events (id),
    student_id uuid NOT NULL REFERENCES accounts (id),
    PRIMARY KEY (event_id, student_id)
);
