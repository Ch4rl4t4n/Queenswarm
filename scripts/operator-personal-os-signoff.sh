#!/usr/bin/env bash
# ST1–ST7 Personal OS signoff — all sprint gates + prod verify + human backlog snapshot.
#
# Usage:
#   ./scripts/operator-personal-os-signoff.sh
#   SKIP_PROD=1 ./scripts/operator-personal-os-signoff.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
OUT_MD="${REPORT_DIR}/PERSONAL_OS_ST7_SIGNOFF_${STAMP}.md"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
SKIP_PROD="${SKIP_PROD:-0}"
FAIL=0

mkdir -p "$REPORT_DIR"

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

run_gate() {
  local script="$1"
  local log="${REPORT_DIR}/signoff-${script%.sh}-${STAMP}.log"
  if [[ -x "${ROOT}/scripts/${script}" ]]; then
    if "${ROOT}/scripts/${script}" >"$log" 2>&1; then
      pass "$script"
      return 0
    fi
    fail "$script (log: $log)"
    return 1
  fi
  fail "missing ${script}"
  return 1
}

echo "=== Personal OS ST1–ST7 Signoff ==="
echo "stamp: ${STAMP}"
echo

echo "--- Sprint gates ---"
for gate in \
  audit-personal-os-discipline-gate.sh \
  audit-personal-os-st2-gate.sh \
  audit-personal-os-st3-gate.sh \
  audit-personal-os-st4-gate.sh \
  audit-personal-os-procedures-gate.sh \
  audit-personal-os-truth-gate.sh; do
  run_gate "$gate" || true
done

echo ""
echo "--- Readiness + verify ---"
READINESS_JSON="$(./scripts/operator-solo-readiness-audit.sh)"
READINESS_STATUS="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['readiness']['status'])" "$READINESS_JSON")"
READINESS_SCORE="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['readiness']['score_pct'])" "$READINESS_JSON")"
if [[ "$READINESS_STATUS" == "ready" ]]; then
  pass "solo-readiness ${READINESS_SCORE}% (${READINESS_STATUS})"
else
  fail "solo-readiness ${READINESS_SCORE}% (${READINESS_STATUS})"
fi

if SKIP_PROD="$SKIP_PROD" ./scripts/operator-personal-os-verify.sh >"${REPORT_DIR}/signoff-verify-${STAMP}.log" 2>&1; then
  pass "operator-personal-os-verify"
else
  fail "operator-personal-os-verify"
fi

echo ""
echo "--- Human backlog snapshot ---"
IL_PENDING="?"
OP5_JSON='{"op5_review":[]}'
if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  docker cp "$ROOT/backend/scripts/operator_st4_task_hygiene.py" "$BACKEND:/app/scripts/operator_st4_task_hygiene.py" 2>/dev/null || true
  OP5_JSON="$(docker exec "$BACKEND" python scripts/operator_st4_task_hygiene.py 2>/dev/null || echo '{}')"
  IL_OUT="$(MIN_PENDING=0 ./scripts/operator-tech-scv-proof.sh 2>/dev/null | tail -1 || true)"
  IL_PENDING="$(echo "$IL_OUT" | sed -n 's/.*pending_proposals=\([0-9]*\).*/\1/p')"
  [[ -z "$IL_PENDING" ]] && IL_PENDING="?"
fi

cat >"$OUT_MD" <<EOF
# Personal OS ST1–ST7 signoff (${STAMP})

Canonical plan: \`docs/OPERATOR_TRUTH_ROADMAP.md\`

## Automated gates

| Gate | Status |
|------|--------|
| ST1 discipline | $(grep -q 'DISCIPLINE GATE.*PASS' "${REPORT_DIR}/signoff-audit-personal-os-discipline-gate-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |
| ST2 routing | $(grep -q 'ST2 GATE: PASS' "${REPORT_DIR}/signoff-audit-personal-os-st2-gate-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |
| ST3 Tech SCV | $(grep -q 'ST3 GATE: PASS' "${REPORT_DIR}/signoff-audit-personal-os-st3-gate-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |
| ST4 adoption | $(grep -q 'ST4 GATE: PASS' "${REPORT_DIR}/signoff-audit-personal-os-st4-gate-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |
| ST5 procedures | $(grep -q 'PROCEDURES GATE.*PASS' "${REPORT_DIR}/signoff-audit-personal-os-procedures-gate-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |
| Operator truth (full) | $(grep -q 'OPERATOR TRUTH (full): PASS' "${REPORT_DIR}/signoff-audit-personal-os-truth-gate-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |
| Solo readiness | ${READINESS_STATUS} (${READINESS_SCORE}%) |
| Personal OS verify | $(grep -q 'PERSONAL OS VERIFY: PASS' "${REPORT_DIR}/signoff-verify-${STAMP}.log" 2>/dev/null && echo PASS || echo see logs) |

## Human-only (not code)

| Item | Action |
|------|--------|
| OP5 | Review promoted digest tasks on \`/tasks\` |
| Innovation Lab | Review ${IL_PENDING} pending Tech SCV proposals |
| ST8 | Voice · Reddit live · Slack — explicit opt-in only |

## OP5 task snapshot

\`\`\`json
${OP5_JSON}
\`\`\`

## Re-run

\`\`\`bash
./scripts/operator-personal-os-signoff.sh
./scripts/audit-personal-os-truth-gate.sh
\`\`\`
EOF

echo ""
echo "Signoff report: ${OUT_MD}"

if [[ "$FAIL" -eq 0 ]]; then
  echo "PERSONAL OS ST1–ST7 SIGNOFF: PASS"
  exit 0
fi
echo "PERSONAL OS ST1–ST7 SIGNOFF: FAIL ($FAIL)"
exit 1
