#!/usr/bin/env bash
# Unified mission readiness — Phase 0 + 1 + 2 + cockpit perf (read-only, no mutations).
# Usage: ./scripts/mission-readiness-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
export ENV_FILE="${ENV_FILE:-.env.prod}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Mission Readiness Audit (Phase 0 → 5 + perf) ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

failed=0
for script in mission-phase0-audit.sh mission-phase1-audit.sh mission-phase2-audit.sh mission-phase5-patterns-audit.sh audit-operator-control-plane-gate.sh; do
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
  if grep -qE '^SOLO_MODE_ENABLED=(true|1|yes)' "$ENV_FILE" 2>/dev/null; then
    echo "Solo mode: commercial P0 (Stripe/billing) DEFERRED — focus on feature audit:"
    echo "  • ./scripts/operator-full-app-audit.sh"
    echo "  • ./scripts/operator-solo-readiness-audit.sh"
    echo "  • docs/AUTHENTICATED_PROD_WALKTHROUGH.md"
  else
    echo "Operator P0 remaining (human-only):"
    echo "  • Stripe keys → ./scripts/operator-p0-close.sh"
    echo "  • Hetzner email → ./scripts/operator-hetzner-send-prep.sh"
    echo "  • See docs/OPERATOR_P0_CLOSE.md"
  fi
  exit 0
fi

echo "Mission readiness: ${failed} phase audit(s) FAILED"
exit 1
