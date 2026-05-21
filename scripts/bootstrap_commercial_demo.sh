#!/usr/bin/env bash
# Idempotent commercial demo bootstrap for prod/stg hosts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${QS_BOOTSTRAP_PASSWORD:-}" ]]; then
  echo "QS_BOOTSTRAP_PASSWORD is required (min 8 chars)." >&2
  exit 1
fi

if docker compose ps --status running backend 2>/dev/null | grep -q backend; then
  exec docker compose exec -T backend python scripts/bootstrap_commercial_demo.py "$@"
fi

exec "$ROOT/backend/venv/bin/python" "$ROOT/backend/scripts/bootstrap_commercial_demo.py" "$@"
