ALTER TABLE campus_events ADD COLUMN created_at timestamptz NOT NULL DEFAULT statement_timestamp();
CREATE INDEX campus_events_feed ON campus_events (created_at DESC, id DESC);
