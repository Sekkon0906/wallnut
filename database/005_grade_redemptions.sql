ALTER TABLE workshop_economies ADD COLUMN points_scope text NOT NULL DEFAULT 'course_only'
    CHECK (points_scope IN ('course_only', 'accepted_courses'));

CREATE TABLE grade_redemption_rules (
    course_id uuid PRIMARY KEY REFERENCES course_sections (id),
    assessment text NOT NULL CHECK (char_length(trim(assessment)) BETWEEN 1 AND 100),
    points_per_step integer NOT NULL CHECK (points_per_step BETWEEN 1 AND 1000000),
    step_milli integer NOT NULL CHECK (step_milli BETWEEN 1 AND 5000),
    max_bonus_milli integer NOT NULL CHECK (max_bonus_milli BETWEEN step_milli AND 5000),
    minimum_grade_milli integer CHECK (minimum_grade_milli BETWEEN 0 AND 5000)
);

CREATE TABLE grade_redemption_sources (
    course_id uuid NOT NULL REFERENCES grade_redemption_rules (course_id),
    source_course_id uuid NOT NULL REFERENCES course_sections (id),
    PRIMARY KEY (course_id, source_course_id)
);

CREATE TABLE simulated_grades (
    course_id uuid NOT NULL,
    student_id uuid NOT NULL,
    base_grade_milli integer NOT NULL CHECK (base_grade_milli BETWEEN 0 AND 5000),
    recorded_by uuid NOT NULL REFERENCES accounts (id),
    PRIMARY KEY (course_id, student_id),
    FOREIGN KEY (course_id, student_id) REFERENCES enrollments (course_id, account_id)
);

CREATE TABLE grade_redemptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_key uuid NOT NULL,
    course_id uuid NOT NULL REFERENCES grade_redemption_rules (course_id),
    student_id uuid NOT NULL,
    assessment text NOT NULL,
    steps integer NOT NULL CHECK (steps BETWEEN 1 AND 5000),
    points bigint NOT NULL CHECK (points BETWEEN 1 AND 5000000000),
    boost_milli integer NOT NULL CHECK (boost_milli BETWEEN 1 AND 5000),
    grade_before_milli integer NOT NULL CHECK (grade_before_milli BETWEEN 0 AND 5000),
    grade_after_milli integer NOT NULL CHECK (
        grade_after_milli = grade_before_milli + boost_milli AND grade_after_milli <= 5000
    ),
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reason text CHECK (char_length(trim(reason)) BETWEEN 1 AND 1000),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    reviewed_at timestamptz,
    reviewed_by uuid REFERENCES accounts (id),
    CHECK (
        (status = 'pending' AND reviewed_by IS NULL AND reviewed_at IS NULL AND reason IS NULL)
        OR (status IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    ),
    CHECK (status <> 'rejected' OR reason IS NOT NULL),
    FOREIGN KEY (course_id, student_id) REFERENCES simulated_grades (course_id, student_id),
    UNIQUE (student_id, request_key)
);

CREATE UNIQUE INDEX grade_redemptions_one_pending ON grade_redemptions (course_id, student_id)
    WHERE status = 'pending';
CREATE INDEX grade_redemptions_by_course ON grade_redemptions (course_id, student_id, status);
CREATE INDEX grade_redemptions_by_student ON grade_redemptions (student_id, status);

CREATE TABLE grade_redemption_debits (
    redemption_id uuid NOT NULL REFERENCES grade_redemptions (id),
    movement_id uuid NOT NULL REFERENCES wallet_movements (id),
    points integer NOT NULL CHECK (points BETWEEN 1 AND 1000000),
    PRIMARY KEY (redemption_id, movement_id)
);

CREATE INDEX grade_debits_by_movement ON grade_redemption_debits (movement_id);
