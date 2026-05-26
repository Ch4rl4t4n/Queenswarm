#!/usr/bin/env bash
# Fast Notion internal integration path for Virtual Company (no OAuth app).
#
# Usage:
#   ./scripts/operator-vc-notion-onboard.sh
#   NOTION_INTEGRATION_TOKEN=secret_xxx APPLY=1 ./scripts/operator-vc-notion-onboard.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TOKENS_FILE="${TOKENS_FILE:-${ROOT}/.env.prod.tokens}"
APPLY="${APPLY:-0}"

echo "== Virtual Company — Notion internal integration =="
echo
echo "Fast path (~88% readiness, activates App Actions router):"
echo "  1. Open https://www.notion.so/my-integrations"
echo "  2. New integration → name: Queenswarm Solo"
echo "  3. Capabilities: read + update content (share pages/databases you need)"
echo "  4. Copy Internal Integration Secret (starts with secret_ or ntn_)"
echo "  5. Either:"
echo "       NOTION_INTEGRATION_TOKEN=secret_… APPLY=1 $0"
echo "     or edit ${TOKENS_FILE}:"
echo "       NOTION_INTEGRATION_TOKEN=secret_…"
echo "       APPLY=1 ./scripts/operator-vc-manual-tokens.sh"
echo

if [[ -n "${NOTION_INTEGRATION_TOKEN:-}" ]]; then
  mkdir -p "$(dirname "$TOKENS_FILE")"
  if [[ ! -f "$TOKENS_FILE" ]]; then
    cp "${ROOT}/.env.prod.tokens.example" "$TOKENS_FILE"
  fi
  if grep -q '^NOTION_INTEGRATION_TOKEN=' "$TOKENS_FILE" 2>/dev/null; then
    sed -i "s|^NOTION_INTEGRATION_TOKEN=.*|NOTION_INTEGRATION_TOKEN=${NOTION_INTEGRATION_TOKEN}|" "$TOKENS_FILE"
  else
    echo "NOTION_INTEGRATION_TOKEN=${NOTION_INTEGRATION_TOKEN}" >>"$TOKENS_FILE"
  fi
  echo "✓ NOTION_INTEGRATION_TOKEN written to ${TOKENS_FILE}"
  APPLY=1
fi

if [[ "$APPLY" == "1" ]]; then
  echo
  APPLY=1 "${ROOT}/scripts/operator-vc-manual-tokens.sh"
else
  echo "When ready: NOTION_INTEGRATION_TOKEN=secret_… APPLY=1 $0"
fi
