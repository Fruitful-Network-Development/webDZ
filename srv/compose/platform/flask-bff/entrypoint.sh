#!/usr/bin/env bash
set -euo pipefail

if [ "${RUN_MIGRATIONS:-}" = "true" ]; then
  if command -v flask >/dev/null 2>&1; then
    echo "Running migrations..."
    flask db upgrade
  else
    echo "RUN_MIGRATIONS requested but flask is not available." >&2
    exit 1
  fi
fi

exec gunicorn -c gunicorn.conf.py "${GUNICORN_APP:-app:app}"
