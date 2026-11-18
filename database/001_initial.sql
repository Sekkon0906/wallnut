CREATE TABLE members (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text UNIQUE NOT NULL CHECK (email = lower(email)),
    handle text UNIQUE NOT NULL CHECK (handle ~ '^[a-z0-9_]{3,24}$'),
    display_name text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 60),
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('student', 'organizer'))
);

CREATE TABLE sessions (
    token_hash text PRIMARY KEY,
    member_id uuid NOT NULL REFERENCES members (id),
    expires_at timestamptz NOT NULL
);

CREATE TABLE activities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organizer_id uuid NOT NULL REFERENCES members (id),
    title text NOT NULL CHECK (length(title) BETWEEN 1 AND 100),
    description text NOT NULL CHECK (length(description) BETWEEN 1 AND 1000),
    location text NOT NULL CHECK (length(location) BETWEEN 1 AND 120),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL CHECK (ends_at > starts_at),
    reward integer NOT NULL CHECK (reward BETWEEN 1 AND 500),
    checkin_hash text,
    checkin_expires_at timestamptz,
    CHECK ((checkin_hash IS NULL) = (checkin_expires_at IS NULL))
);

CREATE INDEX activities_dates ON activities (ends_at, starts_at);

CREATE TABLE point_movements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    kind text NOT NULL CHECK (kind IN ('attendance', 'transfer')),
    sender_id uuid REFERENCES members (id),
    recipient_id uuid NOT NULL REFERENCES members (id),
    activity_id uuid REFERENCES activities (id),
    request_id uuid,
    points integer NOT NULL CHECK (points BETWEEN 1 AND 1000000),
    CHECK (
        (kind = 'attendance' AND sender_id IS NULL AND activity_id IS NOT NULL
            AND request_id IS NULL)
        OR
        (kind = 'transfer' AND sender_id IS NOT NULL AND sender_id <> recipient_id
            AND activity_id IS NULL AND request_id IS NOT NULL)
    ),
    UNIQUE (activity_id, recipient_id),
    UNIQUE (sender_id, request_id)
);

CREATE INDEX point_movements_received ON point_movements (recipient_id, created_at DESC);
CREATE INDEX point_movements_sent ON point_movements (sender_id, created_at DESC);

