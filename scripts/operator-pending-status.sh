#!/usr/bin/env bash
# Emit operator P0 pending/completed status as JSON (read-only).
#
# Usage:
#   ./scripts/operator-pending-status.sh
#   ./scripts/operator-pending-status.sh | jq .
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/operator-pending-${STAMP}.json"

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

latest_report_passed() {
  local glob="$1"
  local latest
  latest="$(ls -1 ${glob} 2>/dev/null | tail -1 || true)"
  [[ -n "$latest" ]] || return 1
  python3 -c "import json,sys; d=json.load(open('${latest}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null
}

mkdir -p "$REPORT_DIR"

walkthrough_auto=false
if latest_report_passed "reports/walkthrough/walkthrough-*.json"; then
  walkthrough_auto=true
fi

ha_chaos=false
latest_report_passed "reports/ha/ha-chaos-*.json" && ha_chaos=true

dr_drill=false
latest_dr="$(ls -1 reports/dr/dr-drill-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "$latest_dr" ]]; then
  python3 -c "import json; d=json.load(open('${latest_dr}')); exit(0 if d.get('backup_duration_sec') is not None else 1)" 2>/dev/null && dr_drill=true
fi

hetzner_draft=false
[[ -f "$(ls -1 reports/hetzner/hetzner-reply-*.txt 2>/dev/null | tail -1 || true)" ]] && hetzner_draft=true
hetzner_sent=false
[[ -f reports/operator/hetzner-sent.txt ]] && hetzner_sent=true

host_exposure=false
if ./scripts/audit-host-exposure.sh >/dev/null 2>&1; then
  host_exposure=true
fi

alertmanager_smoke=false
slack_webhook=false
[[ -n "$(load_kv "$ENV_FILE" SLACK_WEBHOOK_URL || true)" ]] && slack_webhook=true
if ./scripts/alertmanager-smoke.sh >/dev/null 2>&1; then
  alertmanager_smoke=true
fi

check_bool_env() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  val="${val,,}"
  [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]
}

# Publish lane flags default true in backend Settings when unset in .env.prod
check_bool_env_or_default_true() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  [[ -z "${val// }" ]] && return 0
  val="${val,,}"
  [[ "$val" != "false" && "$val" != "0" && "$val" != "no" ]]
}

harness_github_webhook=false
harness_github_secret=false
harness_maintainer_tenant=false
harness_forager_cron=false
check_bool_env QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED && harness_github_webhook=true
[[ -n "$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET || true)" ]] && harness_github_secret=true
[[ -n "$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_POST_MERGE_TENANT_ID || true)" ]] && harness_maintainer_tenant=true
check_bool_env FORAGER_INTELLIGENCE_LOOP_ENABLED && harness_forager_cron=true
harness_webhook_ready=$([[ "$harness_github_webhook" == true && "$harness_github_secret" == true && "$harness_maintainer_tenant" == true ]] && echo true || echo false)

user_jwt_script=false
[[ -f backend/scripts/issue_operator_user_jwt.py ]] && user_jwt_script=true

prod_walkthrough_exit=1
if SKIP_E2E=1 ./scripts/prod-walkthrough-gate.sh >/dev/null 2>&1; then
  prod_walkthrough_exit=0
fi

prod_browser_walkthrough=false
if latest_report_passed "reports/walkthrough/browser-walkthrough-*.json"; then
  prod_browser_walkthrough=true
fi

prod_session_walkthrough=false
if latest_report_passed "reports/walkthrough/session-walkthrough-*.json"; then
  prod_session_walkthrough=true
fi

command_center_gate=false
if latest_report_passed "reports/operator/command-center-*.json"; then
  command_center_gate=true
fi

manual_browser_qa="complete_except_hetzner_send"
if [[ "$command_center_gate" != true || "$prod_browser_walkthrough" != true || "$prod_session_walkthrough" != true ]]; then
  manual_browser_qa="rerun_operator_launch_gate"
fi

manual_hetzner_send="pending"
if [[ "$hetzner_sent" == true ]]; then
  manual_hetzner_send="sent"
elif [[ "$hetzner_draft" == true ]]; then
  manual_hetzner_send="draft_ready_copy_to_mail_client"
fi

cat >"$JSON_OUT" <<EOF
{
  "timestamp_utc": "${STAMP}",
  "hive_base": "${HIVE_BASE}",
  "automated": {
    "mission_dev_phases_0_2": true,
    "prod_walkthrough_gate": $([[ "$prod_walkthrough_exit" -eq 0 ]] && echo true || echo false),
    "prod_browser_walkthrough_gate": ${prod_browser_walkthrough},
    "prod_session_walkthrough_gate": ${prod_session_walkthrough},
    "command_center_gate": ${command_center_gate},
    "user_jwt_auto_mint_script": ${user_jwt_script},
    "walkthrough_evidence_passed": ${walkthrough_auto},
    "ha_chaos_evidence_passed": ${ha_chaos},
    "dr_drill_evidence_passed": ${dr_drill},
    "host_exposure_audit": ${host_exposure}
  },
  "monitoring": {
    "alertmanager_smoke_passed": ${alertmanager_smoke},
    "slack_webhook_configured": ${slack_webhook},
    "pattern_alert_rules_file": true,
    "grafana_dashboard": "queenswarm-agentic-patterns"
  },
  "checkout": {
    "status": "removed",
    "setup_required": false
  },
  "harness": {
    "post_merge_webhook_enabled": ${harness_github_webhook},
    "github_webhook_secret": ${harness_github_secret},
    "post_merge_tenant_id": ${harness_maintainer_tenant},
    "webhook_ready": ${harness_webhook_ready},
    "forager_daily_cron_enabled": ${harness_forager_cron},
    "github_webhook_url": "${HIVE_BASE}/api/v1/queen-maintainer/github-webhook"
  },
  "publish_lane": {
    "social_publish_enabled": $(check_bool_env_or_default_true SOCIAL_PUBLISH_ENABLED && echo true || echo false),
    "social_publish_live_enabled": $(check_bool_env SOCIAL_PUBLISH_LIVE_ENABLED && echo true || echo false),
    "publish_queue_enabled": $(check_bool_env_or_default_true PUBLISH_QUEUE_ENABLED && echo true || echo false),
    "morning_publish_pipeline_enabled": $(check_bool_env_or_default_true MORNING_PUBLISH_PIPELINE_ENABLED && echo true || echo false),
    "first_live_post_doc": $([[ -f docs/OPERATOR_FIRST_LIVE_POST.md ]] && echo true || echo false),
    "oauth_setup_doc": $([[ -f docs/OPERATOR_SOCIAL_OAUTH_SETUP.md ]] && echo true || echo false)
  },
  "hetzner": {
    "reply_draft_ready": ${hetzner_draft},
    "marked_sent": ${hetzner_sent}
  },
  "operator_manual": {
    "browser_walkthrough_sections_1_9": "${manual_browser_qa}",
    "hetzner_abuse_email": "${manual_hetzner_send}"
  },
  "next_commands": [
    "./scripts/operator-next.sh",
    "./scripts/operator-p0-prep-all.sh",
    "docs/OPERATOR_LAUNCH_INDEX.md",
    "./scripts/operator-hetzner-copy-email.sh",
    "./scripts/operator-launch-checklist.sh",
    "./scripts/operator-github-webhook-prep.sh",
    "./scripts/operator-resolve-tenant-id.sh",
    "./scripts/operator-harness-env-prep.sh",
    "./scripts/alertmanager-smoke.sh",
    "./scripts/operator-p0-close.sh",
    "./scripts/operator-hetzner-send-prep.sh",
    "./scripts/operator-launch-gate.sh",
    "./scripts/operator-handoff-pack.sh",
    "docs/OPERATOR_P0_CLOSE.md"
  ],
  "report_file": "$(basename "${JSON_OUT}")"
}
EOF

cat "$JSON_OUT"
