-- Ensure MSS profile msn_id supports SAMRAS-style IDs (TEXT).
-- Idempotent: safe to run multiple times.
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

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'platform'
      AND table_name = 'mss_profile'
      AND column_name = 'parent_msn_id'
      AND data_type <> 'text'
  ) THEN
    ALTER TABLE platform.mss_profile
      ALTER COLUMN parent_msn_id TYPE TEXT USING parent_msn_id::text;
  END IF;
END $$;
