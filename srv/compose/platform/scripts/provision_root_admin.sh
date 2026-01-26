#!/bin/sh
set -eu

USER_ID="${USER_ID:-${1:-}}"
MSN_ID="${MSN_ID:-${2:-}}"

if [ -z "$USER_ID" ] || [ -z "$MSN_ID" ]; then
  echo "Usage: USER_ID=<uuid> MSN_ID=<samras-text-id> $0" >&2
  echo "   or: $0 <uuid> <samras-text-id>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

docker compose exec -T platform_db psql -U platform -d platform \
  -v user_id="$USER_ID" \
  -v msn_id="$MSN_ID" \
  -f - < "$SCRIPT_DIR/provision_root_admin.sql"

docker compose exec -T platform_db psql -U platform -d platform -c \
  "SELECT msn_id, user_id, role FROM platform.mss_profile WHERE user_id='${USER_ID}';"
