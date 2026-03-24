# Demo Portal

This directory is the local-only instance home for the demo portal state.

- Runtime code: `/srv/repo/mycite-core/portals`
- Runtime service: `portal@demo.service`
- Bind address: `127.0.0.1:5303`
- Entry URL: `http://127.0.0.1:5303/portal/system`
- State root: `/srv/webapps/demo-portal/state`

The portal is a shared-runtime instance, not a standalone static site.
For this first pass it is intentionally local-only, `AUTH_MODE=none`, and `PORTAL_READ_ONLY=1`.

To refresh the demo state from the current TFF portal snapshot:

```bash
/srv/webapps/demo-portal/sync-state-from-tff.sh
sudo systemctl restart portal@demo.service
```
