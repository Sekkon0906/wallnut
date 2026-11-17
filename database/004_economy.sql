CREATE TABLE faculty_point_budgets (
    faculty_id uuid PRIMARY KEY REFERENCES accounts (id),
    available_points bigint NOT NULL DEFAULT 0 CHECK (available_points >= 0)
);

CREATE TABLE point_allocations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid UNIQUE NOT NULL,
    faculty_id uuid NOT NULL REFERENCES accounts (id),
    admin_id uuid NOT NULL REFERENCES accounts (id),
    points integer NOT NULL CHECK (points BETWEEN 1 AND 1000000),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE workshop_economies (
    workshop_id uuid PRIMARY KEY REFERENCES workshops (id),
    attendee_points integer NOT NULL CHECK (attendee_points BETWEEN 0 AND 1000000),
    facilitator_points integer NOT NULL CHECK (facilitator_points BETWEEN 0 AND 1000000),
    goal_description text,
    goal_coins integer CHECK (goal_coins BETWEEN 1 AND 1000000),
    coin_cost integer CHECK (coin_cost BETWEEN 1 AND 1000000),
    conversion_points integer CHECK (conversion_points BETWEEN 1 AND 1000000),
    CHECK (
        (goal_description IS NULL AND goal_coins IS NULL
         AND coin_cost IS NULL AND conversion_points IS NULL)
        OR
        (goal_description IS NOT NULL AND char_length(trim(goal_description)) BETWEEN 1 AND 1000
         AND goal_coins IS NOT NULL AND coin_cost IS NOT NULL AND conversion_points IS NOT NULL)
    )
);

ALTER TABLE workshop_evidence ADD UNIQUE (id, workshop_id, student_id);

CREATE TABLE wallet_movements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_id uuid NOT NULL,
    evidence_id uuid NOT NULL,
    student_id uuid NOT NULL,
    faculty_id uuid NOT NULL REFERENCES accounts (id),
    kind text NOT NULL,
    points integer NOT NULL CHECK (points BETWEEN 0 AND 1000000),
    coins integer NOT NULL CHECK (coins BETWEEN -1000000 AND 1000000),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (evidence_id, kind),
    FOREIGN KEY (evidence_id, workshop_id, student_id)
        REFERENCES workshop_evidence (id, workshop_id, student_id),
    CHECK (
        (kind = 'evidence_reward' AND points > 0 AND coins = 0)
        OR (kind = 'goal_coins' AND points = 0 AND coins > 0)
        OR (kind = 'coin_conversion' AND points > 0 AND coins < 0)
    )
);

CREATE INDEX wallet_movements_student ON wallet_movements (student_id, created_at DESC, id DESC);
CREATE INDEX wallet_movements_workshop ON wallet_movements (workshop_id);
