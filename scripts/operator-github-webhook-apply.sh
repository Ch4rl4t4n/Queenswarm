#!/usr/bin/env bash
# Create or update Queen Maintainer GitHub webhook via gh CLI (requires repo admin).
#
# Usage:
#   ./scripts/operator-github-webhook-apply.sh          # dry-run
#   APPLY=1 ./scripts/operator-github-webhook-apply.sh  # create/update hook
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
WEBHOOK_URL="${HIVE_BASE}/api/v1/queen-maintainer/github-webhook"
APPLY="${APPLY:-0}"

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

detect_repo() {
  local remote owner repo
  remote="$(git config --get remote.origin.url 2>/dev/null || true)"
  if [[ "$remote" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    owner="${BASH_REMATCH[1]}"
    repo="${BASH_REMATCH[2]%.git}"
    printf '%s/%s' "$owner" "$repo"
    return 0
  fi
  owner="$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_OWNER || true)"
  repo="$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_REPO || true)"
  if [[ -n "${owner// }" && -n "${repo// }" ]]; then
    printf '%s/%s' "$owner" "$repo"
    return 0
  fi
  return 1
}

REPO="$(detect_repo || true)"
SECRET="$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET || true)"

echo "== Queen Maintainer GitHub webhook apply =="
echo "repo:   ${REPO:-unknown}"
echo "url:    ${WEBHOOK_URL}"
echo "apply:  ${APPLY}"
echo

if [[ -z "${REPO:-}" ]]; then
  echo "Could not resolve GitHub repo — set QUEEN_MAINTAINER_GITHUB_OWNER/REPO or fix git remote." >&2
  exit 1
fi

if [[ -z "${SECRET// }" ]]; then
  echo "QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET missing in ${ENV_FILE}" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI required — install and authenticate first." >&2
  exit 1
fi

existing_id=""
existing_url=""
while IFS= read -r line; do
  id="${line%% *}"
  url="${line#* }"
  if [[ "$url" == "$WEBHOOK_URL" ]]; then
    existing_id="$id"
    existing_url="$url"
    break
  fi
done < <(gh api "repos/${REPO}/hooks" --jq '.[] | "\(.id) \(.config.url)"' 2>/dev/null || true)

if [[ -n "$existing_id" ]]; then
  echo "Found existing hook id=${existing_id} → ${existing_url}"
  if [[ "$APPLY" != "1" ]]; then
    echo "Dry-run: would PATCH hook ${existing_id} with current secret."
    exit 0
  fi
  gh api -X PATCH "repos/${REPO}/hooks/${existing_id}" --input - <<EOF
{
  "active": true,
  "events": ["pull_request"],
  "config": {
    "url": "${WEBHOOK_URL}",
    "content_type": "json",
    "secret": "${SECRET}",
    "insecure_ssl": "0"
  }
}
EOF
  echo "Updated webhook ${existing_id} on ${REPO}"
else
  echo "No hook for ${WEBHOOK_URL} on ${REPO}"
  if [[ "$APPLY" != "1" ]]; then
    echo "Dry-run: would POST new webhook (pull_request events)."
    exit 0
  fi
  gh api -X POST "repos/${REPO}/hooks" --input - <<EOF
{
  "name": "web",
  "active": true,
  "events": ["pull_request"],
  "config": {
    "url": "${WEBHOOK_URL}",
    "content_type": "json",
    "secret": "${SECRET}",
    "insecure_ssl": "0"
  }
}
EOF
  echo "Created webhook on ${REPO}"
fi

echo
echo "Verify ping (GitHub → Settings → Webhooks → Recent Deliveries):"
echo "  curl -sS -o /dev/null -w 'health:%{http_code}\\n' ${HIVE_BASE}/health"
