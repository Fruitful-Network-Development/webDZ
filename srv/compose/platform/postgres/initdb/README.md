# Optional init SQL

Place any optional PostgreSQL initialization scripts in this directory.
Files are executed in alphanumeric order when the Postgres container starts.

## Guidelines

- Use `.sql` files (or `.sql.gz` if you prefer a compressed script).
- Keep secrets (passwords, connection strings, API keys) out of these files.
- If you need to customize Keycloak schemas, add a new file such as
  `01-keycloak-custom.sql` rather than editing the base images directly.

## Example

```sql
-- 01-keycloak-custom.sql
-- Example: create a role used by your local environment
CREATE ROLE keycloak_app NOINHERIT;
```
