#!/usr/bin/env bash
# Agentic OS connector vault checklist — Shopify, Stripe, GA4 Phase 3 presets.
#
# Usage:
#   ./scripts/operator-agentic-os-vault-prep.sh
#   INSTALL=1 ./scripts/operator-agentic-os-vault-prep.sh   # create connector rows (no secrets)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
INSTALL="${INSTALL:-0}"

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
if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend not running — install connectors via UI after deploy."
  exit 0
fi

TOKEN="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
if [[ -z "${TOKEN:-}" ]]; then
  echo "Could not issue operator JWT — install connectors via UI."
  exit 0
fi

export HIVE_BASE TOKEN INSTALL
python3 <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

base = os.environ["HIVE_BASE"]
token = os.environ["TOKEN"]
install = os.environ.get("INSTALL", "0") == "1"

templates = [
    ("shopify_admin_api", "shopify"),
    ("stripe_rest_api", "stripe"),
    ("ga4_data_api", "ga4"),
]


def api(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else {}


def list_dynamic() -> list[dict]:
    data = api("GET", "/api/v1/connectors/dynamic")
    return data.get("items") or [] if isinstance(data, dict) else []


def slug_matches(row: dict, needle: str) -> bool:
    slug = str(row.get("slug") or row.get("connector_slug") or "").lower()
    return needle in slug


items = list_dynamic()
print("Active connectors (slug → active):")
for _tid, needle in templates:
    row = next((r for r in items if slug_matches(r, needle)), None)
    if row is None:
        print(f"  ○ {needle} — not installed yet")
        continue
    active = row.get("is_active", row.get("active", False))
    mark = "✓" if active else "○"
    print(f"  {mark} {row.get('slug', needle)} active={active}")

if not install:
    print()
    print("Tip: INSTALL=1 $0 creates connector rows (secrets still via UI).")
    sys.exit(0)

print()
print("Installing Phase 3 connector shells (no secrets)...")
for template_id, needle in templates:
    items = list_dynamic()
    if any(slug_matches(r, needle) for r in items):
        print(f"  ↳ {template_id}: already installed")
        continue
    try:
        result = api(
            "POST",
            "/api/v1/tools/marketplace/install",
            {"source": "phase3_template", "entry_id": template_id},
        )
        status = result.get("status") or result.get("result") or "installed"
        slug = (result.get("connector") or {}).get("slug") or needle
        print(f"  ✓ {template_id}: {status} ({slug})")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        if exc.code == 422 and "already" in body.lower():
            print(f"  ↳ {template_id}: already exists")
        else:
            print(f"  ✗ {template_id}: HTTP {exc.code} — {body[:160]}")
PY

echo
echo "Seal secrets in Connector Vault only — never .env for Shopify/Stripe API keys."
echo "  Shopify: shop URL + Admin API access token"
echo "  Stripe:  sk_live_... or sk_test_... (REST connector; webhook secret goes to .env.prod)"
echo "  GA4:     OAuth consent + property ID in tool paths"
