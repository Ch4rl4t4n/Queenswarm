#!/usr/bin/env bash
# Agentic OS connector vault checklist — Shopify, Stripe, GA4 Phase 3 presets.
#
# Usage:
#   ./scripts/operator-agentic-os-vault-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"

echo "== Agentic OS Vault prep (Shopify + Stripe + GA4) =="
echo "UI: ${HIVE_BASE}/integrations?tab=connectors"
echo

for tid in shopify_admin_api stripe_rest_api ga4_data_api; do
  if grep -q "template_id=\"${tid}\"" "${ROOT}/backend/app/infrastructure/connectors/phase3/catalog.py"; then
    echo "  ✓ Phase 3 preset: ${tid}"
  else
    echo "  ✗ Missing preset: ${tid}"
  fi
done

echo
if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  TOKEN="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "${TOKEN:-}" ]]; then
    echo "Active connectors (slug → active):"
    curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/connectors" 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    print('  (could not parse connectors response)')
    sys.exit(0)
items = data if isinstance(data, list) else data.get('items') or data.get('connectors') or []
need = {'shopify', 'stripe', 'ga4'}
found = set()
for row in items:
    if not isinstance(row, dict):
        continue
    slug = str(row.get('slug') or row.get('connector_slug') or '').lower()
    active = row.get('is_active', row.get('active', False))
    for n in need:
        if n in slug:
            mark = '✓' if active else '○'
            print(f'  {mark} {slug} active={active}')
            found.add(n)
for n in sorted(need - found):
    print(f'  ○ {n} — not installed yet')
" || echo "  (connectors API unavailable)"
  fi
else
  echo "Backend not running — install connectors via UI after deploy."
fi

echo
echo "Seal secrets in Connector Vault only — never .env for Shopify/Stripe API keys."
