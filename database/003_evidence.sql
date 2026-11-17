CREATE TABLE workshop_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_id uuid NOT NULL REFERENCES workshops (id),
    student_id uuid NOT NULL REFERENCES accounts (id),
    reflection text NOT NULL CHECK (char_length(trim(reflection)) BETWEEN 1 AND 2000),
    photo bytea NOT NULL CHECK (octet_length(photo) BETWEEN 1 AND 8388608),
    photo_content_type text NOT NULL CHECK (photo_content_type = 'image/jpeg'),
    status text NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'returned', 'approved')),
    comment text CHECK (char_length(trim(comment)) BETWEEN 1 AND 1000),
    submitted_at timestamptz NOT NULL DEFAULT now(),
    reviewed_by uuid REFERENCES accounts (id),
    reviewed_at timestamptz,
    CHECK (
        (status = 'submitted' AND reviewed_by IS NULL AND reviewed_at IS NULL AND comment IS NULL)
        OR (status IN ('approved', 'returned') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    ),
    CHECK (status <> 'returned' OR comment IS NOT NULL),
    UNIQUE (workshop_id, student_id)
);
