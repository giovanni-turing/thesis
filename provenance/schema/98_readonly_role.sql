-- 98_readonly_role.sql — read-only query identity for the provenance schema.
-- Apply:  psql ... -v ro_pw="'<password>'" -f 98_readonly_role.sql
-- Reverse: DROP OWNED BY provenance_ro; DROP ROLE provenance_ro;
--
-- NOTE: goku is a SUPERUSER and owns every provenance object, so the goku path
-- (host psql loader + technonous MCP) cannot itself be made read-only — a superuser
-- bypasses all permission checks. This role is the enforceable read-only identity;
-- point any query-only consumer (incl. the MCP, if reconfigurable) at provenance_ro.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='provenance_ro') THEN
    EXECUTE format('CREATE ROLE provenance_ro LOGIN PASSWORD %s', :'ro_pw');
  ELSE
    EXECUTE format('ALTER ROLE provenance_ro LOGIN PASSWORD %s', :'ro_pw');
  END IF;
END $$;
ALTER ROLE provenance_ro SET default_transaction_read_only = on;  -- soft layer
ALTER ROLE provenance_ro SET search_path = provenance, public;
GRANT CONNECT ON DATABASE postgres TO provenance_ro;
GRANT USAGE  ON SCHEMA provenance TO provenance_ro;
GRANT SELECT ON ALL TABLES    IN SCHEMA provenance TO provenance_ro;  -- hard layer: SELECT only
GRANT SELECT ON ALL SEQUENCES IN SCHEMA provenance TO provenance_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE goku IN SCHEMA provenance GRANT SELECT ON TABLES    TO provenance_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE goku IN SCHEMA provenance GRANT SELECT ON SEQUENCES TO provenance_ro;
REVOKE CREATE ON SCHEMA provenance FROM PUBLIC;
