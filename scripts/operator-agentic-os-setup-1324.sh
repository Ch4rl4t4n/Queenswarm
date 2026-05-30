#!/usr/bin/env bash
# Agentic OS operator setup — order: 1 harness → 3 Stripe webhook → 2 Vault → 4 swarms
#
# Usage:
#   ./scripts/operator-agentic-os-setup-1324.sh
#   STRIPE_WEBHOOK_SECRET=whsec_... APPLY=1 ./scripts/operator-agentic-os-setup-1324.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
APPLY="${APPLY:-0}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "=============================================="
echo " Agentic OS setup (1 → 3 → 2 → 4)"
echo "=============================================="
echo

echo "[1/4] Harness — curated memory instructions"
if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "  ✗ Backend not running — start stack first." >&2
  exit 1
fi
docker cp "$ROOT/backend/scripts/bootstrap_agentic_os_harness.py" "$BACKEND:/app/scripts/bootstrap_agentic_os_harness.py"
docker cp "$ROOT/docs/curated_memory_templates/operator_harness_instructions.md.example" \
  "$BACKEND:/app/agentic_os_harness_instructions.md.example"
docker exec "$BACKEND" python scripts/bootstrap_agentic_os_harness.py
echo "  → Verify: ${HIVE_BASE}/settings/harness (Curated memory → instructions)"
echo

echo "[3/4] Stripe commerce webhook"
if [[ "$APPLY" == "1" && -n "${STRIPE_WEBHOOK_SECRET:-}" ]]; then
  STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" APPLY=1 "$ROOT/scripts/operator-commerce-stripe-webhook-prep.sh" || true
else
  "$ROOT/scripts/operator-commerce-stripe-webhook-prep.sh" || true
fi
echo

echo "[2/4] Connector Vault — Shopify + Stripe + GA4"
"$ROOT/scripts/operator-agentic-os-vault-prep.sh"
echo

echo "[4/4] Swarm Builder — E-shop Ops + Marketing Ops"
TOKEN="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n')"
for tmpl in eshop-ops marketing-ops; do
  echo "  Building ${tmpl}..."
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"template_id\": \"${tmpl}\", \"skip_if_exists\": true}" \
    "${HIVE_BASE}/api/v1/virtual-company/build-department-swarm" | python3 -c "
import json, sys
d = json.load(sys.stdin)
b = d.get('build') or {}
print(f\"    status={b.get('status','?')} swarm_id={b.get('swarm_id','')}\")
"
done
echo
echo "Done. Next:"
echo "  • Seal connector secrets in Integrations if not active"
echo "  • If Stripe secret ready: STRIPE_WEBHOOK_SECRET=whsec_... APPLY=1 $0 && deploy"
echo "  • Open ${HIVE_BASE}/apps-tools/ecommerce-automation"
