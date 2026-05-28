#!/usr/bin/env bash
# Bootstrap everything automatable for real operator work (trading, Factory, publish).
#
# Usage:
#   ./scripts/operator-real-work-bootstrap.sh
#   BRAND_NAME="My SaaS Co" ./scripts/operator-real-work-bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
BRAND_NAME="${BRAND_NAME:-Hive Revenue Lab}"

api() {
  local method="$1" path="$2" body="${3:-}"
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "${HIVE_BASE}${path}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$body"
  else
    curl -sS -X "$method" "${HIVE_BASE}${path}" \
      -H "Authorization: Bearer ${TOKEN}"
  fi
}

install_template() {
  local entry_id="$1"
  local resp status
  resp="$(api POST "/api/v1/tools/marketplace/install" \
    "{\"source\":\"phase3_template\",\"entry_id\":\"${entry_id}\"}")"
  status="$(printf '%s' "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo error)"
  echo "  ${entry_id} → ${status}"
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Real-work bootstrap — trading · Factory · publish       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "FAIL: backend not running (${BACKEND})" >&2
  exit 1
fi

TOKEN="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n')"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: operator JWT" >&2
  exit 1
fi

echo "[1/6] Core automation (trio, publish seed, simulate)…"
./scripts/operator-complete-pending.sh || true
echo

echo "[2/6] Virtual Company brand (Factory landing) → ${BRAND_NAME}"
api PUT "/api/v1/virtual-company/profile" \
  "{\"brand_name\":\"${BRAND_NAME}\",\"industry\":\"AI automation\",\"primary_goal\":\"Revenue from agents — trading, mini SaaS, publish\"}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('  brand:', d.get('brand_name'))" 2>/dev/null || echo "  WARN: profile update failed"
echo

echo "[3/6] Marketplace connectors"
install_template "polymarket_gamma_api"
install_template "polymarket_clob_api"
install_template "venice_mcp"
echo

echo "[4/6] OAuth redeploy (reload .env.prod.oauth)"
./scripts/operator-oauth-redeploy.sh
echo

echo "[5/6] Checkout lane"
echo "  In-app checkout removed from this deployment."
echo

echo "[6/6] Status snapshots"
./scripts/operator-publish-lane-status.sh || true
echo
curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/micro-saas-factory" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('Factory:', d.get('progress_pct'), '%', '|', d.get('product_name'))"
echo
curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/solo-operator/publish-onboarding" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('Publish onboarding:', d.get('progress_pct'), '%')
for s in d.get('steps',[]):
    if s.get('status') not in ('done','ready'):
        print('  TODO:', s.get('id'), '-', s.get('status'))
"
echo

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  YOUR 3 steps (need secrets only you can add)            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo
echo "A) META OAuth (~20 min) — live Instagram/FB posts"
echo "   1. https://developers.facebook.com/apps/ → create app"
echo "   2. Edit .env.prod.oauth:"
echo "        OAUTH_META_CLIENT_ID=..."
echo "        OAUTH_META_CLIENT_SECRET=..."
echo "   3. ./scripts/operator-oauth-redeploy.sh"
echo "   4. UI: Integrations → Hub → Connect Instagram"
echo "   Guide: docs/OPERATOR_META_INSTAGRAM_OAUTH.md"
echo
echo "B) Polymarket live trading (~30 min) — real stávky"
echo "   1. UI: Integrations → Polymarket CLOB → seal vault creds"
echo "   2. Fund Polygon wallet on polymarket.com"
echo "   3. APPLY=1 ./scripts/operator-live-trading-prep.sh"
echo "   Guide: docs/OPERATOR_PREDICTION_MARKETS_SETUP.md"
echo
echo "C) Venice media gen (optional, ~5 min)"
echo "   VENICE_API_KEY=sk-... ./scripts/operator-venice-connector-prep.sh"
echo
echo "Checkout lane remains disabled in this deployment."
echo "Hard refresh: ${HIVE_BASE}/"
