#!/usr/bin/env bash
# Phase 6 Queen Maintainer + post-merge webhook audit (read-only).
#
# Usage: ./scripts/mission-phase6-queen-maintainer-audit.sh
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

echo "== Queenswarm Mission Phase 6 — Queen Maintainer Audit =="
echo

echo "[1] Maintainer services + API router"
for path in \
  backend/app/application/services/queen_maintainer/service.py \
  backend/app/application/services/queen_maintainer/post_merge_webhook.py \
  backend/app/application/services/queen_maintainer/pr_workflow.py \
  backend/app/application/services/queen_maintainer/tech_health.py \
  backend/app/presentation/api/routers/queen_maintainer.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'github-webhook' backend/app/presentation/api/routers/queen_maintainer.py; then
  ok "POST /queen-maintainer/github-webhook route"
else
  bad "Missing github-webhook route"
fi
if grep -q 'queen_maintainer_post_merge_webhook_enabled' backend/app/core/config.py; then
  ok "Post-merge webhook config fields"
else
  bad "Missing post-merge webhook config"
fi
echo

echo "[2] Harness snapshot + rate limit exempt"
if grep -q '"queen_maintainer"' backend/app/application/services/harness_snapshot.py; then
  ok "Harness snapshot exposes queen_maintainer status"
else
  bad "harness snapshot missing queen_maintainer"
fi
if grep -q 'queen-maintainer/github-webhook' backend/app/presentation/api/middleware/rate_limit.py; then
  ok "GitHub webhook exempt from rate limit"
else
  bad "Rate limit missing webhook exempt path"
fi
if grep -q 'queen_maintainer_router' backend/app/presentation/api/v1.py; then
  ok "Queen Maintainer router mounted on API v1"
else
  bad "v1.py missing queen_maintainer router"
fi
echo

echo "[3] Frontend harness panel"
if [[ -f frontend/components/hive/queen-maintainer-webhook-panel.tsx ]]; then
  ok "queen-maintainer-webhook-panel.tsx"
else
  bad "Missing queen-maintainer-webhook-panel.tsx"
fi
if grep -q 'QueenMaintainerWebhookPanel' frontend/components/hive/settings-harness-panel.tsx; then
  ok "Settings harness mounts webhook panel"
else
  bad "Webhook panel not mounted"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_queen_maintainer_unit.py \
    backend/tests/test_post_merge_webhook_unit.py \
    backend/tests/test_queen_maintainer_api_unit.py \
    backend/tests/test_harness_snapshot_unit.py \
    --no-cov; then
    ok "Queen Maintainer unit tests pass"
  else
    bad "Queen Maintainer unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
