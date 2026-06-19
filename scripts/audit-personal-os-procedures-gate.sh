#!/usr/bin/env bash
# ST5 Procedures package gate — registry + skill wiring (passes when ST5 shipped).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Procedures Gate (ST5) ==="

if [[ -d procedures ]] || [[ -d backend/app/procedures ]]; then
  pass "procedures registry directory"
else
  fail "ST5 pending — no procedures/ registry (HN1)"
fi

for skill in personal-advisor-playbook community-engagement-playbook closed-review-loop; do
  if [[ -f "backend/app/skills/${skill}.md" ]]; then
    pass "skill ${skill}.md"
  else
    fail "missing skill ${skill}.md"
  fi
done

for proc in advisor advisor-eval community-engage memory-review triage-digest; do
  if [[ -f "procedures/${proc}.md" ]]; then
    pass "procedure ${proc}.md"
  else
    fail "missing procedures/${proc}.md"
  fi
done

if grep -q '/advisor' docs/OPERATOR_TRUTH_ROADMAP.md 2>/dev/null; then
  pass "procedure map documented"
else
  fail "procedure map missing in OPERATOR_TRUTH"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PROCEDURES GATE (ST5): PASS"
  exit 0
fi
echo "PROCEDURES GATE (ST5): FAIL ($FAIL) — ship ST5 after ST1–ST4"
exit 1
