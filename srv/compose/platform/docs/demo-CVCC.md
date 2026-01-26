# CVCC Demo

## 1) Authenticate and capture a session cookie

Use your browser to sign in as root admin and keep the session cookie. The
scripts below require a valid cookie jar, so start here if `/me` returns `401`.

```
https://api.fruitfulnetworkdevelopment.com/login?tenant=platform&return_to=/admin
```

## 2) Seed the CVCC tenant + network data

```
cd /srv/compose/platform
COOKIE_JAR=/tmp/cvcc_cookie.jar ./scripts/demo_cvcc_seed.sh
```

Notes:

- The tenant registry schema does not include `display_name`, so CVCC uses
  `tenant_id` only.
- The script creates local_domain entries for the participant farms table and a
  placeholder entry for "Marilyn Wotowiec".

## 3) Verify the APIs

```
cd /srv/compose/platform
COOKIE_JAR=/tmp/cvcc_cookie.jar ./scripts/demo_cvcc_verify.sh
```

## 4) Manual console checks

- `/admin` should show tenant cards for `platform` and `cvcc`.
- `/admin/tenant/cvcc` should load all tabs.
- `/t/cvcc/console/network` should list the seeded participant farm records.

## 5) Marilyn Wotowiec provisioning step

Once Marilyn’s Keycloak user exists, create an MSS profile mapping
(tenant-admin for demo):

```
POST /api/admin/user-hierarchy
{
  "user_id": "<keycloak-user-uuid>",
  "display_name": "Marilyn Wotowiec",
  "role": "tenant-admin",
  "parent_msn_id": "<root-admin-msn-id (optional)>"
}
```
