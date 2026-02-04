-- Platform correspondence (email domain management) records.
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS platform.correspondence (
  id BIGSERIAL PRIMARY KEY,
  msn_id TEXT NOT NULL,
  source_file TEXT NOT NULL,
  entry_index INT NOT NULL DEFAULT 0,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS correspondence_msn_source_idx
  ON platform.correspondence (msn_id, source_file, entry_index);

CREATE INDEX IF NOT EXISTS correspondence_msn_idx
  ON platform.correspondence (msn_id);
