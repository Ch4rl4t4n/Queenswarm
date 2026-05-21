#!/usr/bin/env bash
# Unified mission readiness — Phase 0 + 1 + 2 + cockpit perf (read-only, no mutations).
# Usage: ./scripts/mission-readiness-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
export ENV_FILE="${ENV_FILE:-.env.prod}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Mission Readiness Audit (Phase 0 → 2 + perf) ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

failed=0
for script in mission-phase0-audit.sh mission-phase1-audit.sh mission-phase2-audit.sh; do
  echo "──────────────────────────────────────────────────────────"
  if ! "./scripts/${script}"; then
    failed=$((failed + 1))
  fi
  echo
done

echo "══════════════════════════════════════════════════════════"
if [[ "$failed" -eq 0 ]]; then
  echo "Mission readiness: ALL PHASE AUDITS PASSED"
  echo
  echo "Operator gates (may still warn until keys added):"
  if ! "./scripts/operator-gates-audit.sh"; then
    echo
    echo "Note: operator-gates-audit reported failures — see above."
  fi
  echo
  echo "Operator P0 remaining (human-only):"
  echo "  • Stripe keys → ./scripts/operator-p0-close.sh"
  echo "  • Hetzner email → ./scripts/operator-hetzner-send-prep.sh"
  echo "  • See docs/OPERATOR_P0_CLOSE.md"
  exit 0
fi

echo "Mission readiness: ${failed} phase audit(s) FAILED"
exit 1
