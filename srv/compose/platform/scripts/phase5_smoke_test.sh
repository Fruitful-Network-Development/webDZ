#!/bin/sh
set -eu

fail=0

echo "== Phase 5 smoke test =="

echo "-- docker compose services"
running="$(docker compose ps --status running --services 2>/dev/null || true)"
for svc in flask_bff platform_db keycloak keycloak_db; do
  if printf "%s\n" "$running" | grep -qx "$svc"; then
    echo "PASS service: $svc"
  else
    echo "FAIL service: $svc"
    fail=1
  fi
done

echo "-- tenant registry files in container"
tenant_files="$(docker exec -i flask_bff find /app/data/tenants -maxdepth 3 -type f -print 2>/dev/null || true)"
if [ -z "$tenant_files" ]; then
  echo "FAIL tenant registry: no files found"
  fail=1
else
  printf "%s\n" "$tenant_files"
  for required in \
    "/app/data/tenants/index.json" \
    "/app/data/tenants/tenant.schema.json" \
    "/app/data/tenants/platform/tenant.json"
  do
    if printf "%s\n" "$tenant_files" | grep -qx "$required"; then
      echo "PASS tenant file: $required"
    else
      echo "FAIL tenant file: $required"
      fail=1
    fi
  done
fi

echo "-- HTTP checks"
health_code="$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health || true)"
if [ "$health_code" = "200" ]; then
  echo "PASS /health -> 200"
else
  echo "FAIL /health -> $health_code"
  fail=1
fi

login_code="$(curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:8001/login?tenant=platform&return_to=/admin" || true)"
if [ "$login_code" = "302" ]; then
  echo "PASS /login -> 302"
else
  echo "FAIL /login -> $login_code"
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "SMOKE TEST: FAIL"
  exit 1
fi

echo "SMOKE TEST: PASS"
