#!/usr/bin/env bash
# Free intel stack prep — Calendar + Polymarket Gamma shells, social OAuth status.
# Commerce (Shopify/Stripe/GA4) intentionally skipped.
#
# Usage:
#   ./scripts/operator-free-intel-prep.sh
#   INSTALL=1 ./scripts/operator-free-intel-prep.sh
#   TEST=1 INSTALL=1 ./scripts/operator-free-intel-prep.sh   # auto-test Polymarket Gamma
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
INSTALL="${INSTALL:-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Free intel prep — Calendar · Polymarket Gamma · Social OAuth ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "Guide: docs/OPERATOR_FREE_INTEL_SETUP.md"
echo

TEMPLATES=(
  "google_calendar:google_calendar:google_calendar"
  "polymarket_gamma_api:polymarket_gamma:polymarket"
)

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend not running — start stack first."
  exit 1
fi

TOKEN="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
if [[ -z "${TOKEN:-}" ]]; then
  echo "Could not mint operator JWT."
  exit 1
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
install = os.environ.get("INSTALL", "1") == "1"
auto_test = os.environ.get("TEST", "0") == "1"

templates = [
    ("google_calendar", "google_calendar", "google_calendar"),
    ("polymarket_gamma_api", "polymarket_gamma", "polymarket"),
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
    return data.get("items") or []


def slug_match(row: dict, needle: str) -> bool:
    slug = str(row.get("slug") or "").lower()
    return needle in slug


print("── Phase 3 shells (Calendar + Polymarket Gamma) ──")
if install:
    for template_id, slug_hint, _needle in templates:
        items = list_dynamic()
        if any(slug_match(r, slug_hint) for r in items):
            print(f"  ↳ {template_id}: already installed")
            continue
        try:
            result = api(
                "POST",
                "/api/v1/tools/marketplace/install",
                {"source": "phase3_template", "entry_id": template_id},
            )
            status = result.get("status") or "installed"
            print(f"  ✓ {template_id}: {status}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            print(f"  ✗ {template_id}: HTTP {exc.code} — {body[:140]}")
else:
    print("  (dry-run — set INSTALL=1 to provision shells)")

print()
print("── Connector roster ──")
items = list_dynamic()
needles = ["gmail", "notion", "github", "google_calendar", "polymarket_gamma", "instagram", "facebook", "twitter"]
for needle in needles:
    row = next((r for r in items if slug_match(r, needle)), None)
    if row is None:
        print(f"  ○ {needle}: not installed")
        continue
    active = row.get("is_active", False)
    mark = "✓" if active else "○"
    print(f"  {mark} {row.get('slug')} active={active} auth={row.get('auth_type')}")

print()
print("── OAuth vendors (hosted consent) ──")
try:
    catalog = api("GET", "/api/v1/oauth/providers")
    providers = catalog if isinstance(catalog, list) else catalog.get("providers") or []
except urllib.error.HTTPError:
    providers = []

for key in ("google_gmail", "google_calendar", "github_rest", "notion_workspace", "instagram_graph", "facebook_graph", "twitter_api_v2"):
    row = next((p for p in providers if p.get("provider_key") == key), None)
    if row is None:
        continue
    cfg = "configured" if row.get("configured") else "missing env"
    print(f"  · {row.get('label', key)}: vendor {cfg}")

print()
print("── Social publish snapshot ──")
try:
    snap = api("GET", "/api/v1/social-publish")
    for ch in snap.get("channels") or []:
        if ch.get("channel") not in {"instagram", "facebook", "twitter", "tiktok"}:
            continue
        flag = "✓" if ch.get("active") else "○"
        print(
            f"  {flag} {ch.get('label')} env={ch.get('env_configured')} "
            f"installed={ch.get('installed')} active={ch.get('active')}"
        )
except urllib.error.HTTPError as exc:
    print(f"  (social-publish probe HTTP {exc.code})")

if auto_test:
    print()
    print("── Auto-test (auth=none connectors) ──")
    items = list_dynamic()
    for row in items:
        slug = str(row.get("slug") or "")
        if slug != "polymarket_gamma" or row.get("is_active"):
            continue
        cid = row.get("id")
        if not cid:
            continue
        try:
            result = api("POST", f"/api/v1/connectors/dynamic/{cid}/test")
            ok = result.get("ok")
            print(f"  {'✓' if ok else '✗'} {slug}: test ok={ok}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            print(f"  ✗ {slug}: HTTP {exc.code} — {body[:120]}")

print()
print("Next: read docs/OPERATOR_FREE_INTEL_SETUP.md and complete OAuth Connect in UI.")
PY

echo
if [[ -x "${ROOT}/scripts/operator-social-oauth-status.sh" ]]; then
  echo "── Social OAuth env probe ──"
  "${ROOT}/scripts/operator-social-oauth-status.sh" 2>&1 | tail -12 || true
fi

echo
echo "Done."
