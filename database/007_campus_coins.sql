ALTER TABLE ardy_profiles ADD COLUMN career text
    CHECK (char_length(career) BETWEEN 2 AND 100 AND career = btrim(career));

CREATE TABLE ardy_item_purchases (
    student_id uuid NOT NULL REFERENCES accounts (id),
    item_id text NOT NULL,
    item_name text NOT NULL,
    price integer NOT NULL CHECK (price > 0),
    id uuid UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (student_id, item_id)
);

CREATE TABLE coin_payment_requests (
    id uuid PRIMARY KEY,
    recipient_id uuid NOT NULL REFERENCES accounts (id),
    amount integer NOT NULL CHECK (amount BETWEEN 1 AND 1000),
    expires_at timestamptz NOT NULL DEFAULT (clock_timestamp() + interval '5 minutes'),
    payer_id uuid REFERENCES accounts (id),
    paid_at timestamptz,
    CHECK ((payer_id IS NULL) = (paid_at IS NULL)),
    CHECK (recipient_id <> payer_id),
    CHECK (paid_at <= expires_at)
);

CREATE INDEX coin_payment_recipient ON coin_payment_requests (recipient_id) WHERE paid_at IS NOT NULL;
CREATE INDEX coin_payment_payer ON coin_payment_requests (payer_id) WHERE paid_at IS NOT NULL;
