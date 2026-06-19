#!/usr/bin/env bash
# OP3 — Stop stale four-lane sessions and revoke orphan Celery tasks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
STALE_HOURS="${STALE_HOURS:-6}"

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  docker cp "$ROOT/backend/scripts/cleanup_zombie_sessions.py" "$BACKEND:/app/scripts/cleanup_zombie_sessions.py"
  docker exec "$BACKEND" python scripts/cleanup_zombie_sessions.py --stale-hours "$STALE_HOURS" --json
else
  cd "$ROOT/backend" && python scripts/cleanup_zombie_sessions.py --stale-hours "$STALE_HOURS" --json
fi
