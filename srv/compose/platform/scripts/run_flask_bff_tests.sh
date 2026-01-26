#!/bin/sh
set -eu

rebuild=0
if [ "${1:-}" = "--build" ]; then
  rebuild=1
fi

if [ "$rebuild" -eq 1 ]; then
  docker compose up -d --force-recreate --build flask_bff
fi

set +e
collect_output="$(docker exec -i flask_bff sh -lc "pytest -q --collect-only" 2>&1)"
collect_status=$?
set -e

if [ "$collect_status" -ne 0 ]; then
  if printf "%s" "$collect_output" | grep -qi "no tests collected"; then
    echo "ERROR: pytest collected zero tests in flask_bff."
    exit 2
  fi
  echo "$collect_output"
  exit 1
fi

docker exec -i flask_bff sh -lc "pytest -q"
