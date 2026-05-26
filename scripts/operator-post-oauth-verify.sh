#!/usr/bin/env bash
# Verify OAuth env + API readiness after filling .env.prod credentials.
#
# Usage:
#   ./scripts/operator-post-oauth-verify.sh
#   REDEPLOY=1 ./scripts/operator-post-oauth-verify.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

ENV_FILE="${ENV_FILE_PROD}"
REDEPLOY="${REDEPLOY:-0}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

load_kv() {
  load_prod_kv "$1"
}

echo "== Post-OAuth verification =="
echo "env: ${ENV_FILE_PROD}"
[[ -f "$ENV_FILE_OAUTH" ]] && echo "oauth overlay: ${ENV_FILE_OAUTH}" || echo "oauth overlay: (missing — run ./scripts/operator-oauth-env-init.sh)"
echo

TOKENS_FILE="${TOKENS_FILE:-${ROOT}/.env.prod.tokens}"
manual_notion=0
manual_github=0
if [[ -f "$TOKENS_FILE" ]]; then
  nt="$(load_kv_file "$TOKENS_FILE" NOTION_INTEGRATION_TOKEN 2>/dev/null || true)"
  gp="$(load_kv_file "$TOKENS_FILE" GITHUB_PAT 2>/dev/null || true)"
  [[ -n "${nt// }" ]] && manual_notion=1
  [[ -n "${gp// }" ]] && manual_github=1
fi
if [[ "$manual_notion" -eq 0 ]]; then
  for fb in "${ROOT}/.env.prod" "${ROOT}/.env"; do
    nt="$(load_kv_file "$fb" NOTION_API_KEY 2>/dev/null || load_kv_file "$fb" NOTION_INTEGRATION_TOKEN 2>/dev/null || true)"
    [[ -n "${nt// }" ]] && manual_notion=1 && break
  done
fi
if [[ "$manual_github" -eq 0 && "${USE_GH_TOKEN:-1}" == "1" ]] && command -v gh >/dev/null 2>&1; then
  gp="$(gh auth token 2>/dev/null || true)"
  [[ -n "${gp// }" ]] && manual_github=1
fi

missing=0
for pair in "OAUTH_NOTION_CLIENT_ID OAUTH_NOTION_CLIENT_SECRET Notion notion_workspace" \
            "OAUTH_GOOGLE_CLIENT_ID OAUTH_GOOGLE_CLIENT_SECRET Gmail gmail_workspace" \
            "OAUTH_GITHUB_CLIENT_ID OAUTH_GITHUB_CLIENT_SECRET GitHub github_rest"; do
  read -r id_key sec_key label slug <<< "$pair"
  id="$(load_kv "$id_key" || true)"
  sec="$(load_kv "$sec_key" || true)"
  manual_ok=0
  case "$slug" in
    notion_workspace) [[ "$manual_notion" -eq 1 ]] && manual_ok=1 ;;
    github_rest) [[ "$manual_github" -eq 1 ]] && manual_ok=1 ;;
  esac
  if [[ -n "${id// }" && -n "${sec// }" ]]; then
    echo "  ✓ ${label} OAuth env keys set"
  elif [[ "$manual_ok" -eq 1 ]]; then
    echo "  ◐ ${label} — manual token path (no OAuth app)"
  else
    echo "  ✗ ${label} — OAuth: ${id_key}/${sec_key} or manual token"
    missing=$((missing + 1))
  fi
done

echo "Social publish OAuth:"
social_missing=0
for pair in "OAUTH_META_CLIENT_ID OAUTH_META_CLIENT_SECRET Meta (IG/FB)" \
            "OAUTH_X_CLIENT_ID OAUTH_X_CLIENT_SECRET X (Twitter)" \
            "OAUTH_TIKTOK_CLIENT_KEY OAUTH_TIKTOK_CLIENT_SECRET TikTok"; do
  read -r id_key sec_key label <<< "$pair"
  id="$(load_kv "$id_key" || true)"
  sec="$(load_kv "$sec_key" || true)"
  if [[ -n "${id// }" && -n "${sec// }" ]]; then
    echo "  ✓ ${label} OAuth env keys set"
  else
    echo "  ✗ ${label} — set ${id_key} + ${sec_key} in .env.prod.oauth"
    social_missing=$((social_missing + 1))
  fi
done
echo

if [[ "$missing" -gt 0 ]]; then
  echo "Status: ${missing} vendor(s) still need credentials"
  echo "  OAuth guide: ./scripts/operator-oauth-register-guide.sh"
  echo "  Manual path:  ./scripts/operator-vc-manual-tokens.sh (Notion token + gh auth for GitHub)"
  echo
fi

if [[ "${social_missing:-0}" -gt 0 ]]; then
  echo "Status: ${social_missing} social publish vendor(s) still need credentials"
  echo "  ./scripts/operator-social-oauth-prep-all.sh"
  echo
fi

if [[ "$REDEPLOY" == "1" ]]; then
  echo "Redeploying backend + frontend (force-recreate for oauth overlay)…"
  "${ROOT}/scripts/operator-oauth-redeploy.sh"
fi

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

echo "Live API check:"
./scripts/operator-oauth-env-prep.sh 2>&1 | grep -E "Status:|configured|redirect" || true
echo

audit=""
if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN:-}" ]]; then
    audit="$(curl -sk -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE:-https://queenswarm.love}/api/v1/virtual-company/readiness-audit" 2>/dev/null || true)"
  fi
fi
if [[ -z "$audit" ]]; then
  audit="$(./scripts/operator-virtual-company-readiness-audit.sh --json-only 2>/dev/null || true)"
fi
if [[ -n "$audit" ]]; then
  score="$(printf '%s' "$audit" | python3 -c "import json,sys; print(json.load(sys.stdin).get('readiness_score',0))" 2>/dev/null || echo 0)"
  connected="$(printf '%s' "$audit" | python3 -c "import json,sys; d=json.load(sys.stdin); op=d.get('oauth_progress') or d.get('checklist',{}).get('oauth_progress') or {}; print(op.get('connected',0))" 2>/dev/null || echo 0)"
  routers="$(printf '%s' "$audit" | python3 -c "import json,sys; d=json.load(sys.stdin); sr=d.get('checklist',{}).get('super_routers',{}); print(f\"{sr.get('active',0)}/{sr.get('provisioned_total',2)}\")" 2>/dev/null || echo "?/2")"
  echo "Readiness: ${score}% · connectors: ${connected}/3 · super routers: ${routers}"
  if [[ "$missing" -eq 0 ]]; then
    echo
    echo "Next: hard refresh → /integrations?tab=studio → Connect Notion + Gmail + GitHub"
    echo "Super routers auto-activate after OAuth callback."
  elif [[ "$connected" -gt 0 ]]; then
    echo
    echo "Partial path active. Next:"
    [[ "$manual_notion" -eq 0 ]] && echo "  • NOTION_INTEGRATION_TOKEN in .env.prod.tokens → APPLY=1 ./scripts/operator-vc-manual-tokens.sh (~88%)"
    echo "  • Gmail: OAUTH_GOOGLE_* in .env.prod.oauth → ./scripts/operator-oauth-redeploy.sh"
  fi
fi

if [[ "$missing" -gt 0 || "${social_missing:-0}" -gt 0 ]]; then
  exit 1
fi
