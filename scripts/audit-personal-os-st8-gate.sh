#!/usr/bin/env bash
# ST8 — Optional ops gate (CE6 · JA7 · OP7–9 · HN6 · Track M).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS ST8 Gate (optional ops) ==="

# HN6 learn-from-source
if [[ -f procedures/learn-from-source.md ]] && [[ -f backend/app/application/services/learn_from_source_service.py ]]; then
  pass "HN6 learn-from-source procedure + service"
else
  fail "HN6 learn-from-source missing"
fi
if grep -q 'learn-from-source' backend/app/presentation/api/routers/solo_operator.py; then
  pass "HN6 API route"
else
  fail "HN6 API route missing"
fi

# CE6 Reddit live policy
if grep -q 'reddit_live_enabled' backend/app/core/config.py && grep -q 'reddit_live_post_allowed' backend/app/application/services/community_engagement_policy.py; then
  pass "CE6 reddit live config + policy"
else
  fail "CE6 reddit live policy missing"
fi

# JA7 voice
if [[ -x scripts/operator-voice-prep.sh ]]; then
  if ST8_JA7_REQUIRE_KEYS=0 ./scripts/operator-voice-prep.sh >/tmp/st8-ja7-$$.log 2>&1; then
    pass "JA7 voice prep"
  else
    fail "JA7 voice prep"
  fi
else
  fail "missing operator-voice-prep.sh"
fi

# OP7 Slack
if [[ -x scripts/operator-slack-alertmanager-prep.sh ]]; then
  if ./scripts/operator-slack-alertmanager-prep.sh >/tmp/st8-op7-$$.log 2>&1; then
    pass "OP7 Slack alertmanager prep"
  else
    fail "OP7 Slack prep"
  fi
else
  fail "missing operator-slack-alertmanager-prep.sh"
fi

# OP8 GitHub Maintainer
for f in scripts/operator-github-webhook-prep.sh backend/app/application/services/queen_maintainer/post_merge_webhook.py; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

# OP9 automation lane
if grep -q 'four-lanes/automation/trigger' backend/app/presentation/api/routers/solo_operator.py; then
  pass "OP9 automation lane API"
else
  fail "OP9 automation trigger route missing"
fi

# Track M local LLM
if [[ -x scripts/audit-local-sovereign-gate.sh ]]; then
  if ./scripts/audit-local-sovereign-gate.sh >/tmp/st8-trackm-$$.log 2>&1; then
    pass "Track M local sovereign gate"
  else
    fail "Track M gate (see /tmp/st8-trackm-$$.log)"
  fi
else
  fail "missing audit-local-sovereign-gate.sh"
fi

echo ""
echo "--- pytest ST8 subset ---"
PYTHON="${ROOT}/backend/venv/bin/python"
if [[ -x "$PYTHON" ]]; then
  if (
    cd "${ROOT}/backend"
    "$PYTHON" -m pytest -q --no-cov --tb=short \
      tests/test_st8_learn_from_source_unit.py \
      tests/test_solo_operator_four_lanes_unit.py::test_trigger_automation_lane_when_lane_found_then_starts_session \
      tests/test_post_merge_webhook_unit.py \
      2>/dev/null
  ); then
    pass "pytest ST8 subset"
  else
    fail "pytest ST8 subset"
  fi
else
  fail "no python for pytest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "ST8 GATE: PASS"
  exit 0
fi
echo "ST8 GATE: FAIL ($FAIL)"
exit 1
