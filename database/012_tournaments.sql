CREATE TABLE campus_tournaments (
    event_id uuid PRIMARY KEY REFERENCES campus_events (id),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE tournament_participants (
    event_id uuid NOT NULL REFERENCES campus_tournaments (event_id),
    student_id uuid NOT NULL,
    PRIMARY KEY (event_id, student_id),
    FOREIGN KEY (event_id, student_id) REFERENCES campus_event_enrollments (event_id, student_id)
);

CREATE TABLE tournament_matches (
    event_id uuid NOT NULL REFERENCES campus_tournaments (event_id),
    round_number integer NOT NULL CHECK (round_number BETWEEN 1 AND 9),
    match_number integer NOT NULL CHECK (match_number BETWEEN 1 AND 256),
    first_id uuid,
    second_id uuid,
    winner_id uuid,
    score text CHECK (char_length(btrim(score)) BETWEEN 1 AND 80),
    PRIMARY KEY (event_id, round_number, match_number),
    FOREIGN KEY (event_id, first_id) REFERENCES tournament_participants (event_id, student_id),
    FOREIGN KEY (event_id, second_id) REFERENCES tournament_participants (event_id, student_id),
    CHECK (first_id <> second_id),
    CHECK (winner_id IS NULL OR winner_id IS NOT DISTINCT FROM first_id
           OR winner_id IS NOT DISTINCT FROM second_id),
    CHECK (score IS NULL OR (winner_id IS NOT NULL AND first_id IS NOT NULL AND second_id IS NOT NULL)),
    CHECK (round_number <> 1 OR first_id IS NOT NULL)
);
