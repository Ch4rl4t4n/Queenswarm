#!/usr/bin/env bash
# Print harness operator env checklist — GitHub webhook, Forager cron, Slack trainer (no secrets).
#
# Usage:
#   ./scripts/operator-harness-env-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

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

check_bool() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  val="${val,,}"
  if [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]; then
    echo "  ✓ ${key}=true"
    return 0
  fi
  echo "  ○ ${key} not enabled (optional)"
  return 1
}

check_key() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  if [[ -n "${val// }" ]]; then
    echo "  ✓ ${key} set"
    return 0
  fi
  echo "  ✗ ${key} missing in ${ENV_FILE}"
  return 1
}

echo "== Operator Harness env prep checklist =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

missing=0

echo "[Queen Maintainer post-merge webhook]"
check_bool QUEEN_MAINTAINER_ENABLED || true
if check_bool QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED; then
  check_key QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET || missing=$((missing + 1))
  check_key QUEEN_MAINTAINER_POST_MERGE_TENANT_ID || missing=$((missing + 1))
fi
echo "  → GitHub webhook URL: ${HIVE_BASE}/api/v1/queen-maintainer/github-webhook"
echo "  → Events: Pull requests (merged), optional push to main"
echo

echo "[Forager Intelligence daily cron]"
if check_bool FORAGER_INTELLIGENCE_LOOP_ENABLED; then
  cron_h="$(load_kv "$ENV_FILE" FORAGER_INTELLIGENCE_CRON_HOUR || echo 6)"
  cron_m="$(load_kv "$ENV_FILE" FORAGER_INTELLIGENCE_CRON_MINUTE || echo 0)"
  echo "  ✓ schedule UTC ${cron_h}:${cron_m} (hive.forager_intelligence_daily_tick)"
else
  echo "  ○ Enable with FORAGER_INTELLIGENCE_LOOP_ENABLED=true"
fi
echo

echo "[Slack harness trainer]"
if check_bool SLACK_HARNESS_TRAINER_ENABLED; then
  check_key SLACK_HARNESS_TRAINER_SIGNING_SECRET || missing=$((missing + 1))
  check_key SLACK_HARNESS_TRAINER_TENANT_ID || missing=$((missing + 1))
fi
echo "  → Slash command: ${HIVE_BASE}/api/v1/harness/slack-trainer/slack-command"
echo

echo "[Alerts]"
check_key SLACK_WEBHOOK_URL || echo "  ○ SLACK_WEBHOOK_URL optional (Alertmanager blackhole without it)"
echo

echo "[LSP bridge]"
check_bool LSP_MCP_BRIDGE_ENABLED || true
echo

if [[ "$missing" -gt 0 ]]; then
  echo "BLOCKED: ${missing} required harness key(s) missing for enabled features."
  exit 1
fi

echo "READY: harness env looks complete for enabled features."
echo "Verify UI: ${HIVE_BASE}/settings/harness"
