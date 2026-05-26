#!/usr/bin/env bash
# Create or merge .env.prod.oauth from example (gitignored overlay for OAuth secrets).
#
# Usage:
#   ./scripts/operator-oauth-env-init.sh              # create if missing
#   MERGE=1 ./scripts/operator-oauth-env-init.sh    # append missing keys from example
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OAUTH_FILE="${ENV_FILE_OAUTH:-${ROOT}/.env.prod.oauth}"
EXAMPLE="${ROOT}/.env.prod.oauth.example"
MERGE="${MERGE:-0}"

echo "== Init OAuth env overlay =="
echo "target: ${OAUTH_FILE}"
echo "MERGE=${MERGE}"
echo

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing ${EXAMPLE}" >&2
  exit 1
fi

merge_missing_keys() {
  local added=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    local key="${line%%=*}"
    key="${key// /}"
    [[ -z "$key" ]] && continue
    if ! grep -q "^${key}=" "$OAUTH_FILE" 2>/dev/null; then
      printf '%s\n' "$line" >>"$OAUTH_FILE"
      echo "  + ${key}"
      added=$((added + 1))
    fi
  done <"$EXAMPLE"
  echo "Merged ${added} key(s) from example into ${OAUTH_FILE}"
}

if [[ -f "$OAUTH_FILE" ]]; then
  if [[ "$MERGE" == "1" ]]; then
    merge_missing_keys
    echo
    echo "Next: ./scripts/operator-oauth-env-prep.sh"
    exit 0
  fi
  echo "Already exists — edit OAuth keys there, or:"
  echo "  MERGE=1 $0   # append missing keys from example (e.g. social publish)"
  echo "  REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
  exit 0
fi

cp "$EXAMPLE" "$OAUTH_FILE"
chmod 600 "$OAUTH_FILE"
echo "Created ${OAUTH_FILE} (mode 600)"
echo
echo "Next:"
echo "  1. ./scripts/operator-oauth-register-guide.sh"
echo "  2. Edit ${OAUTH_FILE} with vendor Client ID + Secret"
echo "  3. REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
