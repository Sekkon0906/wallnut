CREATE TABLE campus_profiles (
    student_id uuid PRIMARY KEY REFERENCES accounts (id),
    bio text NOT NULL DEFAULT '' CHECK (char_length(bio) <= 280),
    visible boolean NOT NULL DEFAULT false,
    show_career boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
