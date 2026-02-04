#!/bin/sh
set -euo pipefail

BASE_URL="${BASE_URL:-https://api.fruitfulnetworkdevelopment.com}"
COOKIE_JAR="${COOKIE_JAR:-/tmp/cvcc_cookie.jar}"

TENANT_ID="cvcc"
CLIENT_DOMAIN="cuyahogavalleycountrysideconservancy.org"
OIDC_CLIENT_ID="flask-bff"
OIDC_CLIENT_SECRET_ENV="CVCC_OIDC_CLIENT_SECRET"

TABLE_LOCAL_ID="b7c0f55a-0d7b-4c1d-8f67-08cf1f2f2a5b"
MARILYN_LOCAL_ID="8e6a3f7d-2b4c-4b92-9321-8f7f6d0a1a31"

FARM_ONE_LOCAL_ID="c9c38b7f-1f65-41b3-9c7f-9f25b0f4f6e2"
FARM_TWO_LOCAL_ID="8c0c29d8-1ad4-4d8b-8d75-fd6d0e5f0b42"

curl_json() {
  method="$1"
  url="$2"
  payload="${3:-}"
  if [ -n "$payload" ]; then
    curl -sS -w "\n%{http_code}" \
      -H "Content-Type: application/json" \
      -X "$method" \
      -d "$payload" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      "$BASE_URL$url"
  else
    curl -sS -w "\n%{http_code}" \
      -X "$method" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      "$BASE_URL$url"
  fi
}

split_response() {
  response="$1"
  status="$(printf "%s" "$response" | tail -n 1)"
  body="$(printf "%s" "$response" | sed '$d')"
  printf "%s\n%s" "$status" "$body"
}

echo "Verifying session with /me ..."
me_response="$(curl_json GET "/me")"
me_status="$(printf "%s" "$me_response" | tail -n 1)"
if [ "$me_status" != "200" ]; then
  echo "Not authenticated. Visit:"
  echo "  ${BASE_URL}/login?tenant=platform&return_to=/admin"
  echo "Then re-run this script with COOKIE_JAR pointing to your session cookie."
  exit 1
fi

tenant_payload="$(cat <<JSON
{
  "tenant_id": "${TENANT_ID}",
  "client_domain": "${CLIENT_DOMAIN}",
  "allowed_return_to": [
    "/admin",
    "/t/${TENANT_ID}/console",
    "/t/${TENANT_ID}/console/network",
    "https://${CLIENT_DOMAIN}"
  ],
  "oidc_client_id": "${OIDC_CLIENT_ID}",
  "oidc_client_secret_env": "${OIDC_CLIENT_SECRET_ENV}",
  "console_modules": {
    "network": true
  }
}
JSON
)"

echo "Ensuring tenant ${TENANT_ID} exists ..."
tenant_get="$(curl_json GET "/api/admin/tenants/${TENANT_ID}")"
tenant_status="$(printf "%s" "$tenant_get" | tail -n 1)"
if [ "$tenant_status" = "404" ]; then
  create_resp="$(curl_json POST "/api/admin/tenants" "$tenant_payload")"
  create_status="$(printf "%s" "$create_resp" | tail -n 1)"
  if [ "$create_status" != "201" ]; then
    echo "Failed to create tenant: $create_resp"
    exit 1
  fi
elif [ "$tenant_status" != "200" ]; then
  echo "Failed to load tenant: $tenant_get"
  exit 1
fi

update_resp="$(curl_json PUT "/api/admin/tenants/${TENANT_ID}" "$tenant_payload")"
update_status="$(printf "%s" "$update_resp" | tail -n 1)"
if [ "$update_status" != "200" ]; then
  echo "Failed to update tenant: $update_resp"
  exit 1
fi

echo "Ensuring local_domain entries ..."
domains_resp="$(curl_json GET "/api/admin/local-domain")"
domains_body="$(printf "%s" "$domains_resp" | sed '$d')"

domain_exists() {
  python3 - "$1" "$domains_body" <<'PY'
import json,sys
target=sys.argv[1]
payload=json.loads(sys.argv[2] or "{}")
domains=payload.get("local_domains", [])
print("yes" if any(row.get("local_id") == target for row in domains) else "no")
PY
}

if [ "$(domain_exists "$TABLE_LOCAL_ID")" != "yes" ]; then
  curl_json POST "/api/admin/local-domain" "$(cat <<JSON
{
  "local_id": "${TABLE_LOCAL_ID}",
  "title": "Participant Farms"
}
JSON
)" >/dev/null
fi

if [ "$(domain_exists "$MARILYN_LOCAL_ID")" != "yes" ]; then
  curl_json POST "/api/admin/local-domain" "$(cat <<JSON
{
  "local_id": "${MARILYN_LOCAL_ID}",
  "title": "Marilyn Wotowiec"
}
JSON
)" >/dev/null
fi

echo "Ensuring archetype participant_farms ..."
archetype_resp="$(curl_json GET "/api/admin/archetypes?tenant_id=${TENANT_ID}")"
archetype_body="$(printf "%s" "$archetype_resp" | sed '$d')"

archetype_id="$(python3 - "$archetype_body" <<'PY'
import json,sys
payload=json.loads(sys.argv[1] or "{}")
for row in payload.get("archetypes", []):
    if row.get("name") == "participant_farms":
        print(row.get("id"))
        break
PY
)"

if [ -z "$archetype_id" ]; then
  create_arch_resp="$(curl_json POST "/api/admin/archetypes" "$(cat <<JSON
{
  "tenant_id": "${TENANT_ID}",
  "name": "participant_farms",
  "fields": [
    {"position": 1, "name": "msn_id", "type": "string"},
    {"position": 2, "name": "local_id", "type": "string"},
    {"position": 3, "name": "logo", "type": "string"},
    {"position": 4, "name": "images", "type": "array"},
    {"position": 5, "name": "bio", "type": "string"},
    {"position": 6, "name": "sources", "type": "array"}
  ]
}
JSON
)")"
  create_arch_body="$(printf "%s" "$create_arch_resp" | sed '$d')"
  archetype_id="$(python3 - "$create_arch_body" <<'PY'
import json,sys
payload=json.loads(sys.argv[1] or "{}")
print(payload.get("id") or "")
PY
)"
fi

if [ -z "$archetype_id" ]; then
  echo "Failed to resolve archetype_id."
  exit 1
fi

echo "Ensuring manifest binding ..."
manifest_resp="$(curl_json GET "/api/admin/manifest?tenant_id=${TENANT_ID}")"
manifest_body="$(printf "%s" "$manifest_resp" | sed '$d')"
manifest_exists="$(python3 - "$manifest_body" "$TABLE_LOCAL_ID" <<'PY'
import json,sys
payload=json.loads(sys.argv[1] or "{}")
table_id=sys.argv[2]
print("yes" if any(row.get("table_id") == table_id for row in payload.get("manifest", [])) else "no")
PY
)"

if [ "$manifest_exists" != "yes" ]; then
  curl_json POST "/api/admin/manifest" "$(cat <<JSON
{
  "tenant_id": "${TENANT_ID}",
  "table_id": "${TABLE_LOCAL_ID}",
  "archetype_id": "${archetype_id}"
}
JSON
)" >/dev/null
fi

echo "Provisioning table ..."
curl_json POST "/api/admin/tables" "$(cat <<JSON
{
  "tenant_id": "${TENANT_ID}",
  "table_local_id": "${TABLE_LOCAL_ID}",
  "mode": "general"
}
JSON
)" >/dev/null || true

echo "Seeding records ..."
records_resp="$(curl_json GET "/api/t/${TENANT_ID}/tables/${TABLE_LOCAL_ID}")"
records_body="$(printf "%s" "$records_resp" | sed '$d')"

record_exists() {
  python3 - "$1" "$records_body" <<'PY'
import json,sys
target=sys.argv[1]
payload=json.loads(sys.argv[2] or "{}")
records=payload.get("records", [])
print("yes" if any((row.get("data") or {}).get("local_id") == target for row in records) else "no")
PY
}

if [ "$(record_exists "$FARM_ONE_LOCAL_ID")" != "yes" ]; then
  curl_json POST "/api/t/${TENANT_ID}/tables/${TABLE_LOCAL_ID}" "$(cat <<JSON
{
  "msn_id": "SAMRAS:cvcc/participant_farms/001",
  "local_id": "${FARM_ONE_LOCAL_ID}",
  "logo": "heritage-hollow.png",
  "images": ["heritage-hollow-1.jpg", "heritage-hollow-2.jpg"],
  "bio": "Heritage Hollow Farm raises pasture poultry and grows heirloom produce for local families.",
  "sources": ["https://example.com/heritage-hollow"]
}
JSON
)" >/dev/null
fi

if [ "$(record_exists "$FARM_TWO_LOCAL_ID")" != "yes" ]; then
  curl_json POST "/api/t/${TENANT_ID}/tables/${TABLE_LOCAL_ID}" "$(cat <<JSON
{
  "msn_id": "SAMRAS:cvcc/participant_farms/002",
  "local_id": "${FARM_TWO_LOCAL_ID}",
  "logo": "riverbend-acres.png",
  "images": ["riverbend-1.jpg"],
  "bio": "Riverbend Acres focuses on regenerative grazing and a small CSA program for the valley.",
  "sources": ["https://example.com/riverbend", "https://example.com/riverbend/story"]
}
JSON
)" >/dev/null
fi

echo "CVCC seed complete."
