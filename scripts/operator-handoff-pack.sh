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

if [[ "$SKIP_RESPONSIVE_E2E" != "1" ]]; then
  run_step "responsive-shell-e2e" bash -c 'cd frontend && CI=1 npx playwright test e2e/responsive-shell.spec.ts --workers=1'
fi

cat >"${OUT_DIR}/README.txt" <<EOF
Queenswarm operator handoff pack (${STAMP})

Automated slice complete. Manual steps:
1. Browser QA — docs/AUTHENTICATED_PROD_WALKTHROUGH.md (sections 1–9, logged in)
2. Stripe — add keys to .env.prod → ./scripts/finish-stripe-setup.sh
3. Hetzner — send hetzner-reply-draft.log to abuse@hetzner.com (AbuseID 11B0286:23)

Re-run full gate:
  SKIP_E2E=1 ./scripts/operator-launch-gate.sh
EOF

echo
echo "== Handoff pack written: ${OUT_DIR} =="
ls -1 "$OUT_DIR"
