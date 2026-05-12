#!/usr/bin/env bash
# Bootstrap or reset one dashboard operator against the Compose ``backend`` container.
#
# Set ``QS_BOOTSTRAP_PASSWORD`` (min 8 chars) in your shell before running. Never commit it.
#
# Examples:
#   QS_BOOTSTRAP_PASSWORD='choose-a-long-secret' \
#     ./scripts/bootstrap-dashboard-operator.sh admin@queenswarm.love --admin
#
#   QS_BOOTSTRAP_PASSWORD='same-or-new-secret' \
#     ./scripts/bootstrap-dashboard-operator.sh admin@queenswarm.love --reset --admin
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EMAIL="${1:?Usage: QS_BOOTSTRAP_PASSWORD='…' ${0##*/} <email> [--admin] [--reset] …}"
shift || true

PASSWORD="${QS_BOOTSTRAP_PASSWORD:-}"
if [ "${#PASSWORD}" -lt 8 ]; then
  echo "bootstrap-dashboard-operator.sh: QS_BOOTSTRAP_PASSWORD must be at least 8 characters." >&2
  exit 1
fi

exec docker compose exec -T \
  -e QS_BOOTSTRAP_PASSWORD="${PASSWORD}" \
  backend python scripts/bootstrap_dashboard_operator.py \
  --email "${EMAIL}" \
  "$@"
