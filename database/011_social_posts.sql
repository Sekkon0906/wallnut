CREATE TABLE social_posts (
    id uuid PRIMARY KEY,
    author_id uuid NOT NULL REFERENCES accounts (id),
    body text NOT NULL CHECK (char_length(body) <= 1200),
    photo bytea,
    creation_digest bytea NOT NULL CHECK (octet_length(creation_digest) = 32),
    revision integer NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz,
    deleted_at timestamptz,
    hidden_at timestamptz,
    moderation_reason text,
    CHECK ((hidden_at IS NULL) = (moderation_reason IS NULL)),
    CHECK (
        (deleted_at IS NULL AND (body <> '' OR photo IS NOT NULL))
        OR (deleted_at IS NOT NULL AND body = '' AND photo IS NULL)
    )
);

CREATE INDEX social_posts_feed ON social_posts (created_at DESC, id DESC) WHERE deleted_at IS NULL;

CREATE TABLE social_post_reports (
    post_id uuid NOT NULL REFERENCES social_posts (id),
    reporter_id uuid NOT NULL REFERENCES accounts (id),
    revision integer NOT NULL CHECK (revision >= 0),
    reason text NOT NULL CHECK (char_length(reason) BETWEEN 3 AND 500),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at timestamptz,
    PRIMARY KEY (post_id, reporter_id, revision)
);

CREATE INDEX social_post_reports_pending
    ON social_post_reports (post_id, created_at DESC, reporter_id) WHERE resolved_at IS NULL;

CREATE TABLE social_post_moderation (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id uuid NOT NULL REFERENCES social_posts (id),
    admin_id uuid NOT NULL REFERENCES accounts (id),
    hidden boolean NOT NULL,
    reason text NOT NULL CHECK (char_length(reason) BETWEEN 3 AND 500),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
