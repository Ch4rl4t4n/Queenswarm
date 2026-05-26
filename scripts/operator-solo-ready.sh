#!/usr/bin/env bash
# One-shot solo operator setup — focus preset, brain pack, publish lane, daily plan.
#
# Usage:
#   ./scripts/operator-solo-ready.sh
#   OVERWRITE_BRAIN=1 ./scripts/operator-solo-ready.sh
#   SKIP_DEPLOY=1 ./scripts/operator-solo-ready.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
OVERWRITE_BRAIN="${OVERWRITE_BRAIN:-0}"
SKIP_DEPLOY="${SKIP_DEPLOY:-0}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Solo Ready — PO · Marketing · Paper trading  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/7] Apply solo mode preset → ${ENV_FILE}"
./scripts/apply-solo-mode.sh

echo
echo "[2/7] Publish lane + Brain Pack (simulate-approved pack)"
if [[ "$OVERWRITE_BRAIN" == "1" ]]; then
  OVERWRITE_BRAIN=1 ./scripts/operator-publish-lane-prep.sh
else
  ./scripts/operator-publish-lane-prep.sh || {
    echo "WARN: publish prep failed — run OVERWRITE_BRAIN=1 if brain pack empty"
  }
fi

echo
echo "[3/7] Deploy (solo daily plan + session presets + dashboard panel)"
if [[ "$SKIP_DEPLOY" != "1" ]]; then
  POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file "$ENV_FILE"
else
  echo "Deploy skipped (SKIP_DEPLOY=1)"
fi

echo
echo "[4/7] Hive policy / curated memory"
if [[ "$OVERWRITE_BRAIN" == "1" ]]; then
  ./scripts/operator-hive-policy-seed.sh --force || true
else
  ./scripts/operator-hive-policy-seed.sh || true
fi

echo
echo "[5/7] Solo lane bootstrap (trio tags + Bank PO weekly routine)"
./scripts/operator-solo-bootstrap-lane.sh || true

echo
echo "[6/7] Solo readiness audit"
./scripts/operator-solo-readiness-audit.sh || true

echo
echo "[7/7] Daily plan probe"
if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/solo-operator/daily-plan" \
      | python3 -m json.tool 2>/dev/null | head -40 || true
  fi
fi

echo
echo "== Solo ready =="
echo "1. Hard refresh → ${HIVE_BASE}/"
echo "2. Dashboard → **Dnešný plán** → Run 3 Bees"
echo "3. /agents?preset=bank-po-brief → Bank PO supervisor session"
echo "4. Settings → AI harness → Operator Hub → publish OAuth when ready"
echo
echo "Docs: docs/SOLO_OPERATOR_TRIO_GUIDE.md · docs/OPERATOR_FIRST_LIVE_POST.md"
