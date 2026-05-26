#!/usr/bin/env bash
# Virtual Company solo bootstrap — free_first routing + readiness checklist (read-only + optional apply).
#
# Usage:
#   ./scripts/operator-virtual-company-bootstrap.sh           # checklist only
#   APPLY=1 ./scripts/operator-virtual-company-bootstrap.sh   # POST bootstrap-solo + checklist
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
APPLY="${APPLY:-0}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "== Virtual Company bootstrap =="
echo "hive: ${HIVE_BASE}"
echo "APPLY=${APPLY}"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"

if [[ "$APPLY" == "1" ]]; then
  echo "[1] Applying solo free_first routing…"
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/virtual-company/bootstrap-solo" | python3 -m json.tool
  echo

  echo "[2] Seeding default operator profile…"
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/virtual-company/seed-default-profile" | python3 -m json.tool
  echo

  echo "[3] Installing free connector templates…"
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/virtual-company/install-free-connectors" | python3 -m json.tool
  echo

  echo "[4] Provisioning solo Super Tool Routers…"
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/virtual-company/provision-solo-routers" | python3 -m json.tool
  echo

  echo "[5] Building all department swarms (+ Sentinel)…"
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"include_sentinel": true}' \
    "${HIVE_BASE}/api/v1/virtual-company/build-all-departments" | python3 -m json.tool
  echo
fi

echo "[6] Bootstrap checklist"
curl -sk -H "Authorization: Bearer ${TOKEN}" \
  "${HIVE_BASE}/api/v1/virtual-company/bootstrap-checklist" | python3 -m json.tool

echo
score="$(curl -sk -H "Authorization: Bearer ${TOKEN}" \
  "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" 2>/dev/null | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('readiness_score',0))" 2>/dev/null || echo 0)"
simulate_done="$(curl -sk -H "Authorization: Bearer ${TOKEN}" \
  "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" 2>/dev/null | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if d.get('simulate_path_complete') else 'no')" 2>/dev/null || echo no)"
if [[ "$simulate_done" == "yes" ]]; then
  echo "Simulate path COMPLETE (${score}% readiness — connectors optional)."
  echo "When ready: ./scripts/operator-vc-notion-onboard.sh"
  echo "UI:   ${HIVE_BASE}/integrations?tab=studio"
elif [[ "$score" -lt 100 ]]; then
  echo "Next blocker: OAuth — run ./scripts/operator-oauth-register-guide.sh"
  echo "Then: REDEPLOY=1 ./scripts/operator-post-oauth-verify.sh"
  echo "UI:   ${HIVE_BASE}/integrations?tab=studio → Connect Notion + Gmail + GitHub"
else
  echo "Next: ${HIVE_BASE}/integrations?tab=studio — all green."
fi
