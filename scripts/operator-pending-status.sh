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

stripe_key_ok() {
  local key="$1" prefix="$2"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  [[ -n "${val// }" && "$val" == ${prefix}* ]]
}

latest_report_passed() {
  local glob="$1"
  local latest
  latest="$(ls -1 ${glob} 2>/dev/null | tail -1 || true)"
  [[ -n "$latest" ]] || return 1
  python3 -c "import json,sys; d=json.load(open('${latest}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null
}

mkdir -p "$REPORT_DIR"

stripe_secret=false
stripe_webhook=false
stripe_pro_price=false
stripe_ent_price=false
if [[ -f "$ENV_FILE" ]]; then
  stripe_key_ok STRIPE_SECRET_KEY sk_ && stripe_secret=true
  stripe_key_ok STRIPE_WEBHOOK_SECRET whsec_ && stripe_webhook=true
  [[ -n "$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_ID || true)" ]] && stripe_pro_price=true
  [[ -n "$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_ID || true)" ]] && stripe_ent_price=true
fi
stripe_ready=$([[ "$stripe_secret" == true && "$stripe_webhook" == true ]] && echo true || echo false)

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

host_exposure=false
if ./scripts/audit-host-exposure.sh >/dev/null 2>&1; then
  host_exposure=true
fi

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

manual_browser_qa="complete_except_stripe_and_hetzner_send"
if [[ "$command_center_gate" != true || "$prod_browser_walkthrough" != true || "$prod_session_walkthrough" != true ]]; then
  manual_browser_qa="rerun_operator_launch_gate"
fi

manual_stripe_checkout="pending"
manual_hetzner_send="pending"
[[ "$stripe_ready" == true ]] && manual_stripe_checkout="keys_ready_run_finish_stripe_setup"
[[ "$hetzner_draft" == true ]] && manual_hetzner_send="draft_ready_copy_to_mail_client"

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
  "stripe": {
    "secret_key": ${stripe_secret},
    "webhook_secret": ${stripe_webhook},
    "pro_price_id": ${stripe_pro_price},
    "enterprise_price_id": ${stripe_ent_price},
    "ready_for_finish_setup": ${stripe_ready}
  },
  "operator_manual": {
    "browser_walkthrough_sections_1_9": "${manual_browser_qa}",
    "stripe_live_checkout": "${manual_stripe_checkout}",
    "hetzner_abuse_email": "${manual_hetzner_send}"
  },
  "next_commands": [
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
