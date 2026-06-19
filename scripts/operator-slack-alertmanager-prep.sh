#!/usr/bin/env bash
# ST8 OP7 — Slack Alertmanager prep (render config + smoke).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"

echo "=== ST8 OP7 Slack Alertmanager prep ==="
echo "Set SLACK_WEBHOOK_URL in ${ENV_FILE} then re-run render + deploy."
echo

if [[ -x ./scripts/render-alertmanager-config.sh ]]; then
  ENV_FILE="$ENV_FILE" ./scripts/render-alertmanager-config.sh
  echo "  OK  render-alertmanager-config.sh"
else
  echo "  FAIL missing render-alertmanager-config.sh" >&2
  exit 1
fi

./scripts/alertmanager-smoke.sh
echo "OP7 SLACK PREP: OK (Slack receiver active only when SLACK_WEBHOOK_URL is set)"
