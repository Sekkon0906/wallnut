CREATE TABLE accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    google_subject text UNIQUE NOT NULL,
    email text UNIQUE NOT NULL CHECK (email = lower(email)),
    display_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('student', 'staff', 'faculty', 'admin')),
    CHECK (
        (role = 'student' AND split_part(email, '@', 2) = 'estudiantesunibague.edu.co')
        OR
        (role <> 'student' AND split_part(email, '@', 2) = 'unibague.edu.co')
    ),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    token_hash bytea PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts (id),
    expires_at timestamptz NOT NULL
);
CREATE INDEX sessions_expires_at ON sessions (expires_at);

CREATE TABLE course_sections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL,
    title text NOT NULL,
    term text NOT NULL,
    section text NOT NULL,
    faculty_id uuid NOT NULL REFERENCES accounts (id),
    UNIQUE (code, term, section)
);

CREATE TABLE enrollments (
    course_id uuid NOT NULL REFERENCES course_sections (id),
    account_id uuid NOT NULL REFERENCES accounts (id),
    confirmed_by uuid NOT NULL REFERENCES accounts (id),
    confirmed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (course_id, account_id)
);

CREATE TABLE workshop_calls (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id uuid NOT NULL REFERENCES course_sections (id),
    title text NOT NULL,
    description text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX workshop_calls_feed ON workshop_calls (created_at DESC, id DESC);

CREATE TABLE facilitator_applications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id uuid NOT NULL REFERENCES workshop_calls (id),
    student_id uuid NOT NULL REFERENCES accounts (id),
    proposal text NOT NULL,
    evidence_url text,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'not_selected')),
    submitted_at timestamptz NOT NULL DEFAULT now(),
    reviewed_at timestamptz,
    UNIQUE (call_id, student_id)
);
CREATE UNIQUE INDEX one_facilitator_per_call
    ON facilitator_applications (call_id) WHERE status = 'approved';
