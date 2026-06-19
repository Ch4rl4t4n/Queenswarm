#!/usr/bin/env bash
# ST3 — Tech SCV Innovation Lab proof gate (OP4).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MIN_PENDING="${MIN_PENDING:-3}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
FAIL=0

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS ST3 Gate (OP4 Tech SCV) ==="

if [[ -x "${ROOT}/scripts/operator-tech-scv-proof.sh" ]]; then
  if MIN_PENDING="$MIN_PENDING" "${ROOT}/scripts/operator-tech-scv-proof.sh" >/tmp/st3-gate-$$.log 2>&1; then
    pass "operator-tech-scv-proof.sh (min_pending=$MIN_PENDING)"
  else
    fail "operator-tech-scv-proof.sh (see /tmp/st3-gate-$$.log)"
  fi
else
  fail "missing operator-tech-scv-proof.sh"
fi

if [[ -x "${ROOT}/scripts/audit-jarvis-intelligence-gate.sh" ]]; then
  if "${ROOT}/scripts/audit-jarvis-intelligence-gate.sh" >/tmp/st3-jarvis-$$.log 2>&1; then
    pass "audit-jarvis-intelligence-gate.sh"
  else
    fail "audit-jarvis-intelligence-gate.sh"
  fi
else
  fail "missing audit-jarvis-intelligence-gate.sh"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "ST3 GATE: PASS"
  exit 0
fi
echo "ST3 GATE: FAIL ($FAIL)"
exit 1
