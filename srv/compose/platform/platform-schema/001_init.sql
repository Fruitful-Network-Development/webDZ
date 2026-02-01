-- Canonical platform schema initializer.
-- Idempotent: safe to run multiple times.

CREATE SCHEMA IF NOT EXISTS platform;

-- Platform-owned identity resolution table.
-- Keyed by Keycloak UUID (sub). No credentials, no MFA state, no client operational data.
CREATE TABLE IF NOT EXISTS platform.user_profiles (
  user_id UUID PRIMARY KEY,
  display_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional: record logins/ops early (useful even in early phase)
CREATE TABLE IF NOT EXISTS platform.audit_log (
  id BIGSERIAL PRIMARY KEY,
  at TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_user_id UUID,
  action TEXT NOT NULL,
  detail JSONB
);
