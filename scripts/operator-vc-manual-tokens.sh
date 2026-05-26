#!/usr/bin/env bash
# Activate Notion + GitHub connectors via manual tokens (no OAuth app registration).
# Gmail still requires Google OAuth in .env.prod.oauth for full 100% readiness.
#
# Usage:
#   cp .env.prod.tokens.example .env.prod.tokens
#   # fill NOTION_INTEGRATION_TOKEN + GITHUB_PAT
#   APPLY=1 ./scripts/operator-vc-manual-tokens.sh
#   DRY_RUN=1 ./scripts/operator-vc-manual-tokens.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
TOKENS_FILE="${TOKENS_FILE:-${ROOT}/.env.prod.tokens}"
APPLY="${APPLY:-0}"
DRY_RUN="${DRY_RUN:-0}"

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then val="${val:1:-1}"; fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

echo "== Virtual Company manual token setup =="
echo "tokens: ${TOKENS_FILE}"
echo "apply:  ${APPLY} dry_run: ${DRY_RUN}"
echo

NOTION_TOKEN="${NOTION_INTEGRATION_TOKEN:-$(load_kv "$TOKENS_FILE" NOTION_INTEGRATION_TOKEN || true)}"
GITHUB_PAT="${GITHUB_PAT:-$(load_kv "$TOKENS_FILE" GITHUB_PAT || true)}"

if [[ -z "${NOTION_TOKEN// }" ]]; then
  for fallback_file in "${ROOT}/.env.prod" "${ROOT}/.env"; do
    NOTION_TOKEN="$(load_kv "$fallback_file" NOTION_API_KEY || load_kv "$fallback_file" NOTION_INTEGRATION_TOKEN || true)"
    [[ -n "${NOTION_TOKEN// }" ]] && echo "  ↳ NOTION token from ${fallback_file}" && break
  done
fi

if [[ -z "${GITHUB_PAT// }" && "${USE_GH_TOKEN:-1}" == "1" ]] && command -v gh >/dev/null 2>&1; then
  GITHUB_PAT="$(gh auth token 2>/dev/null || true)"
  if [[ -n "${GITHUB_PAT// }" ]]; then
    echo "  ↳ GITHUB_PAT from gh auth token (session)"
  fi
fi

have_notion=0
have_github=0
[[ -n "${NOTION_TOKEN// }" ]] && have_notion=1 && echo "  ✓ NOTION_INTEGRATION_TOKEN set"
[[ -n "${GITHUB_PAT// }" ]] && have_github=1 && echo "  ✓ GITHUB_PAT set"
[[ "$have_notion" -eq 0 ]] && echo "  ○ NOTION_INTEGRATION_TOKEN missing (optional for partial apply)"
[[ "$have_github" -eq 0 ]] && echo "  ○ GITHUB_PAT missing — set in .env.prod.tokens or login via gh"
if [[ "$have_notion" -eq 0 ]]; then
  echo
  echo "Notion fast path: ./scripts/operator-vc-notion-onboard.sh"
  echo "  → https://www.notion.so/my-integrations (internal integration, no OAuth app)"
fi
echo

if [[ "$have_notion" -eq 0 && "$have_github" -eq 0 ]]; then
  echo "Need at least one token. Edit ${TOKENS_FILE} or ensure gh auth login."
  exit 1
fi

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run: would patch available connector(s), provision solo routers."
  echo "Run: APPLY=1 $0"
  exit 0
fi

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"

export HIVE_BASE TOKEN NOTION_TOKEN GITHUB_PAT DRY_RUN
python3 <<'PY'
import json, os, sys, urllib.error, urllib.request

base = os.environ["HIVE_BASE"]
token = os.environ["TOKEN"]
notion = os.environ.get("NOTION_TOKEN", "").strip()
github = os.environ.get("GITHUB_PAT", "").strip()
dry = os.environ.get("DRY_RUN") == "1"

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())

items = api("GET", "/api/v1/connectors/dynamic").get("items") or []
by_slug = {str(i.get("slug", "")).lower(): i for i in items if i.get("slug")}

patches = {}
if notion:
    patches["notion_workspace"] = {
        "auth_type": "bearer_token",
        "is_active": True,
        "secrets": {"bearer_token": notion},
    }
if github:
    patches["github_rest"] = {
        "auth_type": "oauth2",
        "is_active": True,
        "secrets": {"oauth2_access_token": github},
    }

if not patches:
    print("No tokens to apply")
    sys.exit(1)

for slug, patch in patches.items():
    row = by_slug.get(slug)
    if not row:
        print(f"✗ connector {slug} not installed — run install-free-connectors first")
        sys.exit(1)
    cid = row["id"]
    if dry:
        print(f"→ would patch {slug} ({cid[:8]}…)")
        continue
    api("PATCH", f"/api/v1/connectors/dynamic/{cid}", patch)
    print(f"✓ patched + activated {slug}")
    vault_body = {"slug": slug, "kind": patch["auth_type"] if patch["auth_type"] != "bearer_token" else "api_key"}
    secrets = patch.get("secrets") or {}
    if slug == "notion_workspace" and secrets.get("bearer_token"):
        vault_body["kind"] = "api_key"
        vault_body["api_key"] = secrets["bearer_token"]
    elif secrets.get("oauth2_access_token"):
        vault_body["kind"] = "oauth2"
        vault_body["oauth2_access_token"] = secrets["oauth2_access_token"]
    if vault_body.get("api_key") or vault_body.get("oauth2_access_token"):
        api("POST", "/api/v1/connectors/vault", vault_body)
        print(f"  ↳ vault sealed for {slug}")

if not dry:
    out = api("POST", "/api/v1/virtual-company/provision-solo-routers", {})
    print("✓ provision solo routers:", json.dumps(out, indent=0)[:200])
    audit = api("GET", "/api/v1/virtual-company/readiness-audit")
    print(f"Readiness: {audit.get('readiness_score')}% · connected {audit.get('oauth_progress', {}).get('connected')}/3")
PY

echo
echo "Gmail still needs Google OAuth in .env.prod.oauth for Marketing/Sales lanes."
echo "UI: ${HIVE_BASE}/integrations?tab=studio"
