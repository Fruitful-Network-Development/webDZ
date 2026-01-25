-- MSS + SAMRAS platform tables.
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS platform.mss_profile (
  msn_id UUID PRIMARY KEY,
  user_id UUID UNIQUE NOT NULL,
  parent_msn_id UUID,
  display_name TEXT,
  role TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.local_domain (
  local_id UUID PRIMARY KEY,
  title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform.archetype (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  name TEXT NOT NULL,
  version INT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.archetype_field (
  archetype_id UUID REFERENCES platform.archetype(id),
  position INT NOT NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  ref_domain TEXT,
  constraints JSONB
);

CREATE TABLE IF NOT EXISTS platform.manifest (
  table_id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  archetype_id UUID REFERENCES platform.archetype(id)
);

CREATE TABLE IF NOT EXISTS platform.samras_layout (
  domain TEXT,
  version INT,
  count_stream BYTEA,
  traversal_spec JSONB,
  PRIMARY KEY (domain, version)
);

CREATE TABLE IF NOT EXISTS platform.samras_archetype (
  id UUID PRIMARY KEY,
  domain TEXT NOT NULL,
  allowed_modes TEXT[],
  description TEXT
);
