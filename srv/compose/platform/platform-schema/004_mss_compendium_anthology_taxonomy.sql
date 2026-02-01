-- MSS compendium, anthology, taxonomy mapping tables.
-- Idempotent: safe to run multiple times.

CREATE SCHEMA IF NOT EXISTS mss;

-- Compendium entry (portal entrypoint metadata).
CREATE TABLE IF NOT EXISTS mss.compendium (
  msn_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  anthology_ref TEXT,
  standardization_ref TEXT,
  entity_type TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Anthology entries (namespace/content index).
CREATE TABLE IF NOT EXISTS mss.anthology_entry (
  msn_id TEXT NOT NULL,
  local_id TEXT NOT NULL,
  title TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (msn_id, local_id)
);

-- Taxonomy entries (scoped by source compendium msn_id).
CREATE TABLE IF NOT EXISTS mss.taxonomy_local_map (
  source_msn_id TEXT NOT NULL,
  taxonomy_id TEXT NOT NULL,
  local_id TEXT,
  title TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (source_msn_id, taxonomy_id)
);

-- MSN entries (scoped by source compendium msn_id).
CREATE TABLE IF NOT EXISTS mss.msn_local_map (
  source_msn_id TEXT NOT NULL,
  msn_id TEXT NOT NULL,
  local_id TEXT,
  title TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (source_msn_id, msn_id)
);

-- Muniment access declarations.
CREATE TABLE IF NOT EXISTS mss.muniment (
  msn_id TEXT NOT NULL,
  opus_local_id TEXT NOT NULL,
  title TEXT,
  muniment TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (msn_id, opus_local_id)
);

CREATE INDEX IF NOT EXISTS anthology_entry_msn_idx
  ON mss.anthology_entry (msn_id);

CREATE INDEX IF NOT EXISTS taxonomy_local_map_taxonomy_idx
  ON mss.taxonomy_local_map (taxonomy_id);

CREATE INDEX IF NOT EXISTS msn_local_map_msn_idx
  ON mss.msn_local_map (msn_id);

CREATE INDEX IF NOT EXISTS muniment_msn_idx
  ON mss.muniment (msn_id);
