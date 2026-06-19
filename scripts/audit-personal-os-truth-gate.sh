#!/usr/bin/env bash
# Operator Truth meta-gate — L2 discipline + L3 adoption config + core platform audits.
#
# Usage:
#   ./scripts/audit-personal-os-truth-gate.sh
#   TIER=core ./scripts/audit-personal-os-truth-gate.sh   # ST1–ST3 blockers only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TIER="${TIER:-full}"
FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Operator Truth Gate (tier=${TIER}) ==="
echo "Canonical: docs/OPERATOR_TRUTH_ROADMAP.md"
echo ""

run_gate() {
  local script="$1"
  if [[ -x "${ROOT}/scripts/${script}" ]]; then
    if "${ROOT}/scripts/${script}" >/tmp/truth-gate-$$.log 2>&1; then
      pass "$script"
    else
      fail "$script (log: /tmp/truth-gate-$$.log)"
    fi
  else
    fail "missing ${script}"
  fi
}

echo "--- L2 Discipline (ST1) ---"
run_gate "audit-personal-os-discipline-gate.sh"
run_gate "audit-personal-os-st2-gate.sh"
run_gate "audit-personal-os-st3-gate.sh"
run_gate "audit-personal-os-st4-gate.sh"

if [[ "$TIER" == "core" ]]; then
  echo ""
  echo "TIER=core — skipping adoption/feature gates"
  if [[ "$FAIL" -eq 0 ]]; then
    echo "OPERATOR TRUTH (core): PASS"
    exit 0
  fi
  echo "OPERATOR TRUTH (core): FAIL ($FAIL)"
  exit 1
fi

echo ""
echo "--- L4 Optional (ST8) ---"
run_gate "audit-personal-os-st8-gate.sh"
for gate in \
  audit-personal-os-gate.sh \
  audit-autopilot-gate.sh \
  audit-jarvis-intelligence-gate.sh \
  audit-community-engagement-gate.sh \
  audit-life-os-gate.sh; do
  run_gate "$gate"
done

echo ""
echo "--- ST5+ Procedures ---"
run_gate "audit-personal-os-procedures-gate.sh"
for gate in \
  audit-personal-os-compound-gate.sh \
  audit-research-bee-gate.sh; do
  run_gate "$gate"
done

echo ""
if [[ -f docs/OPERATOR_TRUTH_ROADMAP.md ]] && [[ -f docs/JARVIS_PERSONAL_ADVISOR_SETUP.md ]]; then
  pass "operator truth docs present"
else
  fail "missing OPERATOR_TRUTH or JARVIS setup doc"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "OPERATOR TRUTH (full): PASS"
  exit 0
fi
echo "OPERATOR TRUTH (full): FAIL ($FAIL)"
exit 1
