CREATE TABLE workshops (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id uuid UNIQUE NOT NULL REFERENCES workshop_calls (id),
    facilitator_id uuid NOT NULL REFERENCES accounts (id),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL CHECK (ends_at > starts_at),
    location text NOT NULL CHECK (length(btrim(location)) BETWEEN 1 AND 160),
    capacity integer NOT NULL CHECK (capacity BETWEEN 1 AND 300),
    attendance_code_hash bytea,
    attendance_code_expires_at timestamptz,
    CHECK ((attendance_code_hash IS NULL) = (attendance_code_expires_at IS NULL)),
    CHECK (attendance_code_expires_at <= ends_at),
    FOREIGN KEY (call_id, facilitator_id)
        REFERENCES facilitator_applications (call_id, student_id)
);

CREATE INDEX workshops_starts_at ON workshops (starts_at, id);

CREATE TABLE workshop_enrollments (
    workshop_id uuid NOT NULL REFERENCES workshops (id),
    student_id uuid NOT NULL REFERENCES accounts (id),
    enrolled_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workshop_id, student_id)
);

CREATE TABLE workshop_attendance (
    workshop_id uuid NOT NULL,
    student_id uuid NOT NULL,
    checked_in_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workshop_id, student_id),
    FOREIGN KEY (workshop_id, student_id)
        REFERENCES workshop_enrollments (workshop_id, student_id)
);
