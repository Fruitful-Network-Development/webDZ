#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="/srv/compose/portals/state/tff_portal"
TARGET_ROOT="/srv/webapps/demo-portal/state"

mkdir -p "${TARGET_ROOT}"
rsync -a --delete "${SOURCE_ROOT}/" "${TARGET_ROOT}/"
chmod -R g+rwX "${TARGET_ROOT}"
