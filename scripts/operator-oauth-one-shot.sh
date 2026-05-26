#!/usr/bin/env bash
# Single entry point for Virtual Company OAuth blocker — status, guide, env path.
#
# Usage:
#   ./scripts/operator-oauth-one-shot.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OAUTH_FILE="${ENV_FILE_OAUTH:-${ROOT}/.env.prod.oauth}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Virtual Company OAuth — solo blocker (Priority 1)          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

"${ROOT}/scripts/operator-vc-status-report.sh" 2>&1 | sed '1d'
echo

if [[ ! -f "$OAUTH_FILE" ]]; then
  echo "[1] Creating OAuth overlay file…"
  "${ROOT}/scripts/operator-oauth-env-init.sh"
  echo
fi

echo "[2] Vendor registration guide"
echo "    File to edit: ${OAUTH_FILE}"
echo "    Consoles:    ./scripts/operator-oauth-open-vendors.sh"
echo
"${ROOT}/scripts/operator-oauth-register-guide.sh" 2>&1 | tail -20
echo

echo "── Alternative: Notion + GitHub without OAuth apps ─────────"
echo "  cp .env.prod.tokens.example .env.prod.tokens"
echo "  # NOTION_INTEGRATION_TOKEN + GITHUB_PAT"
echo "  APPLY=1 ./scripts/operator-vc-manual-tokens.sh"
echo "  (Gmail still needs Google OAuth in .env.prod.oauth)"
echo
echo "── After filling ${OAUTH_FILE} ──"
echo "  ./scripts/operator-oauth-redeploy.sh"
echo "  ./scripts/operator-post-oauth-verify.sh"
echo "  open https://queenswarm.love/integrations?tab=studio"
echo

"${ROOT}/scripts/operator-oauth-env-prep.sh" 2>&1 | grep -E "Status:|✓|✗" | tail -6 || true
