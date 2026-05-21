#!/usr/bin/env bash
# Phase 6 Slack harness trainer audit (read-only).
#
# Usage: ./scripts/mission-phase6-slack-harness-trainer-audit.sh
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

echo "== Queenswarm Mission Phase 6 — Slack Harness Trainer Audit =="
echo

echo "[1] Backend service + routes"
if [[ -f backend/app/application/services/slack_harness_trainer.py ]]; then
  ok "slack_harness_trainer.py"
else
  bad "Missing slack_harness_trainer.py"
fi
if grep -q 'slack-trainer/feedback' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/slack-trainer/feedback"
else
  bad "Missing feedback route"
fi
if grep -q 'slack-trainer/slack-command' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/slack-trainer/slack-command"
else
  bad "Missing slash command route"
fi
if grep -q 'slack_harness_trainer_enabled' backend/app/core/config.py; then
  ok "slack_harness_trainer config fields"
else
  bad "Missing slack_harness_trainer config"
fi
if grep -q 'slack-trainer/slack-command' backend/app/presentation/api/middleware/rate_limit.py; then
  ok "Rate limit exempt for Slack ingress"
else
  bad "Slack command not rate-limit exempt"
fi
echo

echo "[2] Feature flag + harness snapshot"
if grep -q '"slack_harness_trainer"' backend/app/application/services/platform_features.py; then
  ok "slack_harness_trainer in platform_features.py"
else
  bad "slack_harness_trainer missing from platform_features"
fi
if grep -q 'slack_trainer' backend/app/application/services/harness_snapshot.py; then
  ok "harness snapshot exposes slack_trainer status"
else
  bad "harness snapshot missing slack_trainer"
fi
echo

echo "[3] Frontend harness panel"
if [[ -f frontend/components/hive/slack-harness-trainer-panel.tsx ]]; then
  ok "slack-harness-trainer-panel.tsx"
else
  bad "Missing slack-harness-trainer-panel.tsx"
fi
if grep -q 'SlackHarnessTrainerPanel' frontend/components/hive/settings-harness-panel.tsx; then
  ok "Settings harness mounts trainer panel"
else
  bad "Trainer panel not mounted"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_slack_harness_trainer_unit.py \
    backend/tests/test_slack_harness_trainer_api_unit.py \
    --no-cov; then
    ok "slack harness trainer tests pass"
  else
    bad "slack harness trainer tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
