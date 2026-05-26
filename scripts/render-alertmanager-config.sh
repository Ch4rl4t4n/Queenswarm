#!/usr/bin/env bash
# Render Alertmanager config from ENV_FILE (uses SLACK_WEBHOOK_URL when set).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-${ENV_FILE:-.env.prod}}"
OUT="${ROOT}/deploy/alertmanager/alertmanager.generated.yml"
BLACKHOLE="${ROOT}/deploy/alertmanager/alertmanager-blackhole.yml"
TEMPLATE="${ROOT}/deploy/alertmanager/alertmanager-slack.yml.template"

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
      if [[ "$val" == \"*\" ]]; then
        val="${val:1:-1}"
      fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

webhook="$(load_kv "$ENV_FILE" SLACK_WEBHOOK_URL || true)"
mkdir -p "$(dirname "$OUT")"

if [[ -z "${webhook// }" ]]; then
  cp "$BLACKHOLE" "$OUT"
  echo "render-alertmanager-config: SLACK_WEBHOOK_URL unset — blackhole receiver (alerts visible in Prometheus only)."
  exit 0
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE"
  exit 1
fi

# Escape single quotes for YAML single-quoted string.
escaped="${webhook//\'/\'\'}"
sed "s|__SLACK_WEBHOOK_URL__|${escaped}|g" "$TEMPLATE" >"$OUT"
echo "render-alertmanager-config: Slack receiver enabled → ${OUT}"
