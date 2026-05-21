#!/usr/bin/env bash
# Collect operator handoff evidence — read-only audits saved under reports/.
#
# Usage:
#   ./scripts/operator-handoff-pack.sh
#   SKIP_E2E=1 ./scripts/operator-handoff-pack.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${ROOT}/reports/operator-handoff-${STAMP}"
mkdir -p "$OUT_DIR"

export HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
export ENV_FILE="${ENV_FILE:-.env.prod}"
SKIP_E2E="${SKIP_E2E:-1}"
SKIP_RESPONSIVE_E2E="${SKIP_RESPONSIVE_E2E:-1}"

echo "== Operator handoff pack =="
echo "output: ${OUT_DIR}"
echo

run_step() {
  local name="$1"
  shift
  local log="${OUT_DIR}/${name}.log"
  echo "[collect] ${name} → ${log##*/}"
  if "$@" >"$log" 2>&1; then
    echo "  OK ${name}"
    return 0
  fi
  echo "  WARN ${name} — see ${log##*/}" >&2
  return 0
}

run_step "mission-readiness" ./scripts/mission-readiness-audit.sh
run_step "operator-gates" ./scripts/operator-gates-audit.sh
run_step "prod-walkthrough" env SKIP_E2E="$SKIP_E2E" ./scripts/prod-walkthrough-gate.sh
run_step "host-exposure" ./scripts/audit-host-exposure.sh
run_step "hetzner-reply-draft" ./scripts/hetzner-abuse-reply.sh
run_step "operator-pending-status" ./scripts/operator-pending-status.sh

run_step "prod-command-center" ./scripts/prod-command-center-gate.sh
run_step "prod-browser-walkthrough" env SKIP_PROD_PUBLIC=0 ./scripts/prod-browser-walkthrough-gate.sh
run_step "prod-session-walkthrough" ./scripts/prod-session-walkthrough-gate.sh

latest_hetzner="$(ls -1 reports/hetzner/hetzner-reply-*.txt 2>/dev/null | tail -1 || true)"
if [[ -n "$latest_hetzner" ]]; then
  cp "$latest_hetzner" "${OUT_DIR}/hetzner-reply.txt"
  echo "[collect] hetzner-reply.txt (copy from reports/hetzner/)"
fi
latest_pending="$(ls -1 reports/operator/operator-pending-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "$latest_pending" ]]; then
  cp "$latest_pending" "${OUT_DIR}/operator-pending.json"
  echo "[collect] operator-pending.json"
fi

latest_session="$(ls -1 reports/walkthrough/session-walkthrough-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "$latest_session" ]]; then
  cp "$latest_session" "${OUT_DIR}/session-walkthrough.json"
  echo "[collect] session-walkthrough.json"
fi

latest_cc="$(ls -1 reports/operator/command-center-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "$latest_cc" ]]; then
  cp "$latest_cc" "${OUT_DIR}/command-center.json"
  echo "[collect] command-center.json"
fi
latest_browser="$(ls -1 reports/walkthrough/browser-walkthrough-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "$latest_browser" ]]; then
  cp "$latest_browser" "${OUT_DIR}/browser-walkthrough.json"
  echo "[collect] browser-walkthrough.json"
fi

if [[ "$SKIP_RESPONSIVE_E2E" != "1" ]]; then
  run_step "responsive-shell-e2e" bash -c 'cd frontend && CI=1 npx playwright test e2e/responsive-shell.spec.ts --workers=1'
fi

cat >"${OUT_DIR}/README.txt" <<EOF
Queenswarm operator handoff pack (${STAMP})

Automated slice complete. Manual steps:
1. Stripe — add keys to .env.prod → ./scripts/operator-p0-close.sh
2. Hetzner — ./scripts/operator-hetzner-send-prep.sh (send draft to abuse@hetzner.com)
3. See docs/OPERATOR_P0_CLOSE.md

Status JSON: operator-pending-status.log

Re-run full gate:
  SKIP_E2E=1 ./scripts/operator-launch-gate.sh
EOF

echo
echo "== Handoff pack written: ${OUT_DIR} =="
ls -1 "$OUT_DIR"
