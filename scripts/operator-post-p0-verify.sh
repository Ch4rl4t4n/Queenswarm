#!/usr/bin/env bash
# Post-P0 verification — run after operator launch prep.
#
# Usage:
#   ./scripts/operator-post-p0-verify.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
export ENV_FILE="${ENV_FILE:-.env.prod}"
SKIP_E2E="${SKIP_E2E:-1}"
SKIP_RESPONSIVE_E2E="${SKIP_RESPONSIVE_E2E:-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Post-P0 Verify                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/3] Launch checklist"
rc=0
./scripts/operator-launch-checklist.sh || rc=$?
if [[ "$rc" -eq 0 || "$rc" -eq 2 ]]; then
  echo "  ✓ Launch checklist pass"
else
  exit "$rc"
fi
echo

echo "[2/3] Launch gate (automated evidence)"
SKIP_E2E="$SKIP_E2E" SKIP_RESPONSIVE_E2E="$SKIP_RESPONSIVE_E2E" ./scripts/operator-launch-gate.sh
echo

echo "[3/3] Final handoff pack"
SKIP_E2E="$SKIP_E2E" SKIP_RESPONSIVE_E2E="$SKIP_RESPONSIVE_E2E" ./scripts/operator-final-handoff.sh
echo

echo "== Post-P0 verify: OK =="
echo "Manual browser: ${HIVE_BASE}/integrations?tab=skills → unlock premium skill"
