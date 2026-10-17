#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker Compose required on enterprise-approved host.' >&2; exit 2; }
[ -f .env ] || { echo 'Copy .env.example to .env and supply a secure administrator token.' >&2; exit 2; }
PUID="$(id -u)" PGID="$(id -g)" export PUID PGID
mkdir -p studio-data; chmod 700 studio-data
if [ "$(id -u)" = "0" ]; then
  echo 'Refusing to launch from a root shell. Use an approved nonroot operator.' >&2; exit 2
fi
# Refuse an obvious unconfigured secret; do not echo token values.
grep -q '^MUSITU_STUDIO_ADMIN_TOKEN=' .env || { echo 'Missing admin token setting' >&2; exit 2; }
if grep -q '^MUSITU_STUDIO_ADMIN_TOKEN=REPLACE_WITH' .env; then
  echo 'Refusing example credential' >&2; exit 2
fi
exec docker compose --env-file .env up --build -d
