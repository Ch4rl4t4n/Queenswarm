#!/usr/bin/env bash
# Phase 4 Voice Overnight Report readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-overnight-voice-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

pytest_bin() {
  if [[ -x "$ROOT/backend/venv/bin/pytest" ]]; then
    echo "$ROOT/backend/venv/bin/pytest"
  else
    echo ""
  fi
}

echo "== Queenswarm Mission Phase 4 — Voice Overnight Report Audit =="
echo

echo "[1] Backend service + route"
if [[ -f backend/app/application/services/overnight_voice_report.py ]]; then
  ok "overnight_voice_report.py"
else
  bad "Missing overnight_voice_report.py"
fi
if grep -q 'overnight-report/voice' backend/app/presentation/api/routers/dump_sleep.py; then
  ok "GET /dump-sleep/overnight-report/voice route"
else
  bad "Missing voice route"
fi
echo

echo "[2] Feature flag"
if grep -q '"overnight_voice_report"' backend/app/application/services/platform_features.py; then
  ok "overnight_voice_report in platform_features.py"
else
  bad "overnight_voice_report missing from platform_features.py"
fi
if grep -q 'overnight_voice_report:' frontend/lib/platform-features.ts; then
  ok "overnight_voice_report in platform-features.ts"
else
  bad "overnight_voice_report missing from platform-features.ts"
fi
echo

echo "[3] Frontend player"
if [[ -f frontend/components/hive/overnight-voice-report-player.tsx ]]; then
  ok "overnight-voice-report-player.tsx"
else
  bad "Missing overnight-voice-report-player.tsx"
fi
if grep -q 'OvernightVoiceReportPlayer' frontend/components/hive/dreaming-summary-card.tsx; then
  ok "DreamingSummaryCard mounts voice player"
else
  bad "Voice player not on dashboard dreaming card"
fi
if grep -q 'OvernightVoiceReportPlayer' frontend/components/ballroom/dump-sleep-panel.tsx; then
  ok "DumpSleepPanel mounts voice player"
else
  bad "Voice player not on Ballroom dump panel"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov \
    tests/test_overnight_voice_report_unit.py \
    tests/test_overnight_voice_report_api_unit.py); then
    ok "overnight voice unit + API tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 4 Voice overnight audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
