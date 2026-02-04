-- Provision or update a root-admin MSS profile.
-- Usage:
--   psql -v user_id=... -v msn_id=... -f provision_root_admin.sql

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'platform'
      AND table_name = 'mss_profile'
      AND column_name = 'msn_id'
      AND data_type <> 'text'
  ) THEN
    ALTER TABLE platform.mss_profile
      ALTER COLUMN msn_id TYPE TEXT USING msn_id::text;
  END IF;
END $$;

INSERT INTO platform.mss_profile (msn_id, user_id, display_name, role)
VALUES (:'msn_id', (:'user_id')::uuid, 'root-admin', 'root-admin')
ON CONFLICT (user_id) DO UPDATE
SET msn_id = EXCLUDED.msn_id,
    display_name = EXCLUDED.display_name,
    role = 'root-admin';
