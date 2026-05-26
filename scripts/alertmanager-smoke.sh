#!/usr/bin/env bash
# Alertmanager + pattern alert smoke — infrastructure checks and optional Slack ping.
#
# Usage:
#   ./scripts/alertmanager-smoke.sh
#   ALERTMANAGER_SMOKE_SEND=1 ./scripts/alertmanager-smoke.sh   # inject ephemeral test alert (Slack if configured)
#
# Writes JSON evidence to reports/operator/alertmanager-smoke-*.json
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
ALERTMANAGER_SMOKE_SEND="${ALERTMANAGER_SMOKE_SEND:-0}"

base_compose=(docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "${ENV_FILE}")

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

mkdir -p "$REPORT_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
json_report="${REPORT_DIR}/alertmanager-smoke-${stamp}.json"

passed=true
checks=()
slack_configured=false
webhook="$(load_kv "$ENV_FILE" SLACK_WEBHOOK_URL || true)"
[[ -n "${webhook// }" ]] && slack_configured=true

note_check() {
  local name="$1" ok="$2" detail="${3:-}"
  checks+=("{\"name\":\"${name}\",\"ok\":${ok},\"detail\":\"${detail}\"}")
  if [[ "$ok" != true ]]; then
    passed=false
  fi
}

echo "== alertmanager-smoke =="

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}"
  exit 1
fi

chmod +x "${ROOT}/scripts/render-alertmanager-config.sh"
"${ROOT}/scripts/render-alertmanager-config.sh" "$ENV_FILE" >/dev/null

cfg="${ROOT}/deploy/alertmanager/alertmanager.generated.yml"
if [[ -f "$cfg" ]]; then
  note_check "config_rendered" true "deploy/alertmanager/alertmanager.generated.yml"
else
  note_check "config_rendered" false "missing generated config"
fi

if docker run --rm --entrypoint amtool -v "${cfg}:/cfg.yml:ro" prom/alertmanager:v0.27.0 check-config /cfg.yml >/dev/null 2>&1; then
  note_check "amtool_check_config" true ""
else
  note_check "amtool_check_config" false "invalid alertmanager config"
fi

am_id="$("${base_compose[@]}" ps -q alertmanager 2>/dev/null || true)"
if [[ -n "${am_id// }" ]]; then
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$am_id" 2>/dev/null || echo unknown)"
  if [[ "$health" == "healthy" || "$health" == "none" ]]; then
    note_check "alertmanager_container" true "health=${health}"
  else
    note_check "alertmanager_container" false "health=${health}"
  fi
else
  note_check "alertmanager_container" false "container not running"
fi

if "${base_compose[@]}" exec -T alertmanager wget -qO- http://127.0.0.1:9093/-/ready >/dev/null 2>&1; then
  note_check "alertmanager_ready" true ""
else
  note_check "alertmanager_ready" false "/-/ready failed"
fi

prom_am="$("${base_compose[@]}" exec -T prometheus wget -qO- 'http://127.0.0.1:9090/api/v1/alertmanagers' 2>/dev/null || echo '{}')"
active_count="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',{}).get('activeAlertmanagers',[])))" <<<"$prom_am" 2>/dev/null || echo 0)"
if [[ "${active_count:-0}" -ge 1 ]]; then
  note_check "prometheus_alertmanager_discovery" true "active=${active_count}"
else
  note_check "prometheus_alertmanager_discovery" false "no active alertmanagers"
fi

prom_rules="$("${base_compose[@]}" exec -T prometheus wget -qO- 'http://127.0.0.1:9090/api/v1/rules?type=alert' 2>/dev/null || echo '{}')"
pattern_rules="$(python3 -c "
import json,sys
d=json.load(sys.stdin)
names=[]
for g in d.get('data',{}).get('groups',[]):
  for r in g.get('rules',[]):
    if r.get('type')=='alerting' and str(r.get('name','')).startswith('Pattern'):
      names.append(r['name'])
print(len(names))
" <<<"$prom_rules" 2>/dev/null || echo 0)"
if [[ "${pattern_rules:-0}" -ge 3 ]]; then
  note_check "pattern_alert_rules" true "count=${pattern_rules}"
else
  note_check "pattern_alert_rules" false "expected>=3 got=${pattern_rules}"
fi

receiver="$(grep -E '^  receiver:' "$cfg" 2>/dev/null | head -1 | awk '{print $2}' || echo unknown)"
if [[ "$slack_configured" == true ]]; then
  if [[ "$receiver" == "slack-queenswarm" ]]; then
    note_check "slack_receiver" true "slack-queenswarm"
  else
    note_check "slack_receiver" false "expected slack-queenswarm got ${receiver}"
  fi
else
  if [[ "$receiver" == "blackhole" ]]; then
    note_check "slack_receiver" true "blackhole (SLACK_WEBHOOK_URL unset)"
  else
    note_check "slack_receiver" false "expected blackhole got ${receiver}"
  fi
fi

smoke_send_ok=false
if [[ "$ALERTMANAGER_SMOKE_SEND" == "1" ]]; then
  echo "-- injecting ephemeral smoke alert (ends in 90s)"
  ends_at="$(date -u -d '+90 seconds' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+90S +%Y-%m-%dT%H:%M:%SZ)"
  starts_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  payload="$(cat <<EOF
[{
  "labels": {
    "alertname": "QueenswarmAlertmanagerSmokeTest",
    "severity": "warning",
    "pattern_id": "smoke"
  },
  "annotations": {
    "summary": "Alertmanager smoke test — safe to ignore (auto-expires)"
  },
  "startsAt": "${starts_at}",
  "endsAt": "${ends_at}"
}]
EOF
)"
  if "${base_compose[@]}" exec -T alertmanager wget -qO- \
    --header='Content-Type: application/json' \
    --post-data="$payload" \
    http://127.0.0.1:9093/api/v2/alerts >/dev/null 2>&1; then
    sleep 2
    found="$("${base_compose[@]}" exec -T alertmanager wget -qO- http://127.0.0.1:9093/api/v2/alerts 2>/dev/null || echo '[]')"
    if python3 -c "import json,sys; alerts=json.load(sys.stdin); sys.exit(0 if any(a.get('labels',{}).get('alertname')=='QueenswarmAlertmanagerSmokeTest' for a in alerts) else 1)" <<<"$found" 2>/dev/null; then
      smoke_send_ok=true
      note_check "smoke_alert_injected" true "QueenswarmAlertmanagerSmokeTest"
      if [[ "$slack_configured" == true ]]; then
        echo "  Slack ping expected if webhook is valid."
      fi
    else
      note_check "smoke_alert_injected" false "alert not visible in /api/v2/alerts"
    fi
  else
    note_check "smoke_alert_injected" false "POST /api/v2/alerts failed"
  fi
else
  note_check "smoke_alert_injected" true "skipped (set ALERTMANAGER_SMOKE_SEND=1 to test delivery)"
fi

checks_json="$(printf '%s\n' "${checks[@]}" | paste -sd, -)"

cat >"$json_report" <<EOF
{
  "timestamp_utc": "${stamp}",
  "passed": ${passed},
  "slack_webhook_configured": ${slack_configured},
  "receiver": "${receiver}",
  "smoke_send_requested": $([[ "$ALERTMANAGER_SMOKE_SEND" == "1" ]] && echo true || echo false),
  "smoke_send_ok": ${smoke_send_ok},
  "checks": [${checks_json}]
}
EOF

echo "Report: ${json_report}"
if [[ "$passed" == true ]]; then
  echo "alertmanager-smoke: PASSED"
  exit 0
fi
echo "alertmanager-smoke: FAILED"
exit 1
