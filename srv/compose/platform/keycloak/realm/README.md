# Keycloak realm exports

Place exported Keycloak realm JSON files in this directory for local development.
Avoid committing secrets or credentials in realm exports.

## Export a realm

From a running Keycloak container, you can export a realm file:

```bash
/opt/keycloak/bin/kc.sh export \
  --dir /opt/keycloak/data/import \
  --realm <realm-name> \
  --users realm_file
```

Copy the exported JSON into this directory (for example,
`my-realm-export.json`).

## Import a realm

Keycloak will import realm files from `/opt/keycloak/data/import` at startup.
Mount this directory into the container and ensure the file is present.

## Keep secrets out of Git

- Remove or redact user passwords, client secrets, and external identity
  provider credentials before committing.
- Prefer environment variables or secret management for sensitive values.
