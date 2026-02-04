-- Remove legacy platform tables to avoid schema drift.
-- Idempotent: safe to run multiple times.

DROP TABLE IF EXISTS platform.local_list_member CASCADE;
DROP TABLE IF EXISTS platform.local_list CASCADE;
DROP TABLE IF EXISTS platform.general_table CASCADE;
DROP TABLE IF EXISTS platform.manifest CASCADE;
DROP TABLE IF EXISTS platform.archetype_field CASCADE;
DROP TABLE IF EXISTS platform.archetype CASCADE;
DROP TABLE IF EXISTS platform.local_domain CASCADE;
DROP TABLE IF EXISTS platform.mss_profile CASCADE;
DROP TABLE IF EXISTS platform.audit_log CASCADE;
DROP TABLE IF EXISTS platform.user_profiles CASCADE;
