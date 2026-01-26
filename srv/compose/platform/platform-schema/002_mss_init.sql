-- MSS + SAMRAS platform tables.
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS platform.mss_profile (
  msn_id TEXT PRIMARY KEY,
  user_id UUID UNIQUE NOT NULL,
  parent_msn_id TEXT,
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

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS platform.general_table (
  tenant_id TEXT NOT NULL,
  table_local_id UUID NOT NULL,
  mode TEXT NOT NULL,
  table_name TEXT NOT NULL,
  archetype_id UUID NOT NULL REFERENCES platform.archetype(id),
  msn_id TEXT,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (tenant_id, table_local_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS general_table_name_idx
  ON platform.general_table (table_name);

CREATE TABLE IF NOT EXISTS platform.local_list (
  list_local_id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  name TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform.local_list_member (
  list_local_id UUID REFERENCES platform.local_list(list_local_id) ON DELETE CASCADE,
  ordinal INT NOT NULL,
  local_id UUID NOT NULL REFERENCES platform.local_domain(local_id),
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (list_local_id, ordinal)
);

CREATE UNIQUE INDEX IF NOT EXISTS local_list_member_local_id_idx
  ON platform.local_list_member (list_local_id, local_id);

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
