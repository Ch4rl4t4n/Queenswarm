#!/usr/bin/env bash
# Monitoring gate — Alertmanager + pattern alert pipeline smoke (read-only).
#
# Usage:
#   ./scripts/monitoring-gate.sh
#   ALERTMANAGER_SMOKE_SEND=1 ./scripts/monitoring-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"

echo "== Queenswarm monitoring gate =="
chmod +x "${ROOT}/scripts/render-alertmanager-config.sh" "${ROOT}/scripts/alertmanager-smoke.sh"
"${ROOT}/scripts/render-alertmanager-config.sh" "$ENV_FILE"
"${ROOT}/scripts/alertmanager-smoke.sh"
echo
echo "Monitoring gate: OK"
echo "Evidence: $(ls -1 "${REPORT_DIR}"/alertmanager-smoke-*.json 2>/dev/null | tail -1 || echo 'none')"
