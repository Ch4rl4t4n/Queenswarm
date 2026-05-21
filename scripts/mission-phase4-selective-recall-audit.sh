#!/usr/bin/env bash
# Phase 4 Selective recall readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-selective-recall-audit.sh
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

echo "== Queenswarm Mission Phase 4 — Selective Recall Audit =="
echo

echo "[1] Backend service + graph vault lane"
for path in \
  backend/app/application/services/selective_recall.py \
  backend/app/domain/hive_mind/service.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'vault_document_recall_for_prompt' backend/app/domain/hive_mind/graph.py; then
  ok "vault_document_recall_for_prompt helper"
else
  bad "Missing vault_document_recall_for_prompt"
fi
if grep -q 'recall-settings' backend/app/presentation/api/routers/hive_mind.py; then
  ok "hive-mind recall settings routes"
else
  bad "Missing recall settings routes"
fi
if grep -q 'hive_mind_selective_recall_enabled' backend/app/core/config.py; then
  ok "selective recall config flags"
else
  bad "Missing selective recall config"
fi
echo

echo "[2] Feature flag"
if grep -q '"selective_recall"' backend/app/application/services/platform_features.py; then
  ok "selective_recall in platform_features.py"
else
  bad "selective_recall missing from platform_features.py"
fi
if grep -q 'selective_recall:' frontend/lib/platform-features.ts; then
  ok "selective_recall in platform-features.ts"
else
  bad "selective_recall missing from platform-features.ts"
fi
echo

echo "[3] Frontend panel"
if [[ -f frontend/components/hive/selective-recall-panel.tsx ]]; then
  ok "selective-recall-panel.tsx"
else
  bad "Missing selective-recall-panel.tsx"
fi
if grep -q 'SelectiveRecallPanel' frontend/components/hive/knowledge-page-client.tsx; then
  ok "Knowledge page mounts SelectiveRecallPanel"
else
  bad "SelectiveRecallPanel not mounted"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov tests/test_selective_recall_unit.py tests/hive_mind/test_hive_mind.py); then
    ok "selective recall + hive_mind unit tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 4 Selective recall audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
