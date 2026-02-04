#!/bin/sh
set -eu

if [ -z "${PLATFORM_DB_URL:-}" ]; then
  echo "Missing PLATFORM_DB_URL env var" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/import_statonomy_samras.py" "$@"
