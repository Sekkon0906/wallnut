CREATE TABLE ardy_nuts (
    id uuid PRIMARY KEY,
    student_id uuid NOT NULL REFERENCES accounts (id),
    item_id text NOT NULL,
    price integer NOT NULL CHECK (price > 0),
    taps integer NOT NULL DEFAULT 0 CHECK (taps BETWEEN 0 AND 3),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (student_id, item_id)
);

CREATE UNIQUE INDEX ardy_nuts_one_pending ON ardy_nuts (student_id) WHERE taps < 3;
CREATE INDEX ardy_nuts_latest ON ardy_nuts (student_id, created_at DESC, id DESC);
