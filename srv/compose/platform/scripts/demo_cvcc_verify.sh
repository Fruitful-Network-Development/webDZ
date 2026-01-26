#!/bin/sh
set -euo pipefail

BASE_URL="${BASE_URL:-https://api.fruitfulnetworkdevelopment.com}"
COOKIE_JAR="${COOKIE_JAR:-/tmp/cvcc_cookie.jar}"

TENANT_ID="cvcc"
TABLE_LOCAL_ID="b7c0f55a-0d7b-4c1d-8f67-08cf1f2f2a5b"

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

expect_status() {
  response="$1"
  expected="$2"
  status="$(printf "%s" "$response" | tail -n 1)"
  if [ "$status" != "$expected" ]; then
    echo "Expected status ${expected}, got ${status}"
    echo "$response"
    exit 1
  fi
  printf "%s" "$response" | sed '$d'
}

me_response="$(curl_json GET "/me")"
expect_status "$me_response" "200" >/dev/null

tenants_body="$(expect_status "$(curl_json GET "/api/admin/tenants")" "200")"
python3 - "$tenants_body" <<'PY'
import json,sys
payload=json.loads(sys.argv[1] or "{}")
tenants=payload.get("tenants", [])
assert "cvcc" in tenants, "cvcc tenant not found"
print("Tenant cvcc present.")
PY

tables_body="$(expect_status "$(curl_json GET "/api/admin/tables?tenant_id=${TENANT_ID}")" "200")"
python3 - "$tables_body" "$TABLE_LOCAL_ID" <<'PY'
import json,sys
payload=json.loads(sys.argv[1] or "{}")
target=sys.argv[2]
tables=payload.get("tables", [])
assert any(row.get("table_local_id") == target for row in tables), "table not provisioned"
print("General table provisioned.")
PY

records_body="$(expect_status "$(curl_json GET "/api/t/${TENANT_ID}/tables/${TABLE_LOCAL_ID}")" "200")"
python3 - "$records_body" <<'PY'
import json,sys
payload=json.loads(sys.argv[1] or "{}")
records=payload.get("records", [])
assert len(records) >= 2, "expected at least 2 records"
print(f"Records present: {len(records)}")
PY

cat <<EOF
Manual URLs:
- ${BASE_URL}/login?tenant=platform&return_to=/admin
- ${BASE_URL}/admin/tenants
- ${BASE_URL}/admin/tenant/cvcc
- ${BASE_URL}/t/cvcc/console
- ${BASE_URL}/t/cvcc/console/network
EOF
