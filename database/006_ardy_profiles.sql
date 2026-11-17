CREATE TABLE ardy_profiles (
    student_id uuid PRIMARY KEY REFERENCES accounts (id),
    avatar jsonb NOT NULL CHECK (jsonb_typeof(avatar) = 'object'),
    show_in_ranking boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ardy_ranking_members ON ardy_profiles (student_id) WHERE show_in_ranking;
