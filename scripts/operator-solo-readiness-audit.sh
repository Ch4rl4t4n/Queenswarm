#!/usr/bin/env bash
# Solo operator readiness audit — modules, env, harness, LLM keys, accounts (read-only JSON).
#
# Usage:
#   ./scripts/operator-solo-readiness-audit.sh
#   ./scripts/operator-solo-readiness-audit.sh | jq .
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
PG_CONTAINER="${PG_CONTAINER:-${COMPOSE_PROJECT}-postgres-1}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/solo-readiness-${STAMP}.json"

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

check_bool_env() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  val="${val,,}"
  [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]
}

check_key_set() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  [[ -n "${val// }" ]]
}

mkdir -p "$REPORT_DIR"

PENDING_JSON="$(./scripts/operator-pending-status.sh 2>/dev/null || echo '{}')"

# Solo mode flag
solo_mode=false
check_bool_env SOLO_MODE_ENABLED && solo_mode=true

personal_os_mode=false
check_bool_env PERSONAL_OS_MODE_ENABLED && personal_os_mode=true

# LLM keys (env layer — tenant keys may also exist in DB)
llm_grok=false
llm_anthropic=false
llm_openai=false
check_key_set GROK_API_KEY && llm_grok=true
check_key_set ANTHROPIC_API_KEY && llm_anthropic=true
check_key_set OPENAI_API_KEY && llm_openai=true
llm_any=$([[ "$llm_grok" == true || "$llm_anthropic" == true || "$llm_openai" == true ]] && echo true || echo false)
llm_tenant_build_allowed=false
llm_tenant_source="none"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-queenswarm_prod-backend-1}"
if [[ "$llm_any" != true ]] && docker ps --format '{{.Names}}' | grep -qx "$BACKEND_CONTAINER"; then
  TENANT_LLM_TOKEN="$(docker exec "$BACKEND_CONTAINER" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "${TENANT_LLM_TOKEN// }" ]]; then
    TENANT_LLM_JSON="$(curl -sS -H "Authorization: Bearer ${TENANT_LLM_TOKEN}" \
      "${HIVE_BASE}/api/v1/factory-readiness/llm" 2>/dev/null || true)"
    if [[ -n "${TENANT_LLM_JSON// }" ]]; then
      llm_tenant_build_allowed="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('build_allowed') else 'false')" "$TENANT_LLM_JSON" 2>/dev/null || echo false)"
      if [[ "$llm_tenant_build_allowed" == "true" ]]; then
        llm_any=true
        llm_tenant_source="tenant_factory_readiness"
      fi
    fi
  fi
fi

# Optional module env flags
env_forager=false
env_simulations=false
env_lsp=false
env_rubric=false
env_episodic=false
env_slack_trainer=false
check_bool_env FORAGER_INTELLIGENCE_LOOP_ENABLED && env_forager=true
check_bool_env SIMULATIONS_ENABLED && env_simulations=true
check_bool_env LSP_MCP_BRIDGE_ENABLED && env_lsp=true
check_bool_env RUBRIC_TEMPLATES_ENABLED && env_rubric=true
check_bool_env EPISODIC_MEMORY_ENABLED && env_episodic=true
check_bool_env SLACK_HARNESS_TRAINER_ENABLED && env_slack_trainer=true

# Platform matrix overrides from Postgres
PLATFORM_OVERRIDES_JSON='{}'
if docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
  PLATFORM_OVERRIDES_JSON="$(docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -tA -c \
    "SELECT COALESCE(json_object_agg(feature_key, enabled), '{}'::json)::text FROM platform_feature_policies WHERE profile_key='environment';" \
    2>/dev/null || echo '{}')"
fi

# Dashboard accounts
active_accounts=0
extra_accounts=0
operator_email="${OPERATOR_EMAIL:-admin@queenswarm.love}"
if docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
  active_accounts="$(docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -tA -c \
    "SELECT count(*) FROM dashboard_users WHERE is_active = true;" 2>/dev/null || echo 0)"
  extra_accounts="$(docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -tA -c \
    "SELECT count(*) FROM dashboard_users WHERE is_active = true AND lower(email) <> lower('${operator_email}');" 2>/dev/null || echo 0)"
fi

# Optional modules expected ON for full solo admin stack
SOLO_OPTIONAL=(
  foragers simulations jobs external_projects episodic_memory
  slack_harness_trainer lsp_mcp_bridge rubric_templates venice_mcp_preset
)

optional_modules_report=""
missing_modules=""
enabled_count=0
for mod in "${SOLO_OPTIONAL[@]}"; do
  enabled_in_db="$(python3 -c "
import json, sys
d = json.loads('''${PLATFORM_OVERRIDES_JSON}''')
print('true' if d.get('${mod}') else 'false')
" 2>/dev/null || echo false)"
  if [[ "$enabled_in_db" == "true" ]]; then
    enabled_count=$((enabled_count + 1))
    optional_modules_report="${optional_modules_report}  ${mod}: on (matrix)\n"
  else
    missing_modules="${missing_modules}${mod},"
    optional_modules_report="${optional_modules_report}  ${mod}: off (matrix)\n"
  fi
done

core_solo_env_ok=$([[ "$solo_mode" == true ]] && echo true || echo false)

# Score: how many checklist items pass
checks_passed=0
checks_total=9
[[ "$solo_mode" == true ]] && checks_passed=$((checks_passed + 1))
[[ "$llm_any" == true ]] && checks_passed=$((checks_passed + 1))
[[ "$enabled_count" -ge 9 ]] && checks_passed=$((checks_passed + 1))
[[ "$env_forager" == true ]] && checks_passed=$((checks_passed + 1))
[[ "$extra_accounts" == "0" ]] && checks_passed=$((checks_passed + 1))
[[ "$(python3 -c "import json; d=json.loads('''${PENDING_JSON}'''); print(d.get('automated',{}).get('host_exposure_audit', False))" 2>/dev/null)" == "True" ]] && checks_passed=$((checks_passed + 1))
[[ "$(python3 -c "import json; d=json.loads('''${PENDING_JSON}'''); print(d.get('automated',{}).get('command_center_gate', False))" 2>/dev/null)" == "True" ]] && checks_passed=$((checks_passed + 1))
[[ "$(python3 -c "import json; d=json.loads('''${PENDING_JSON}'''); print(d.get('hetzner',{}).get('marked_sent', False))" 2>/dev/null)" == "True" ]] && checks_passed=$((checks_passed + 1))

discipline_ok=false
if [[ -x "${ROOT}/scripts/audit-personal-os-discipline-gate.sh" ]]; then
  if "${ROOT}/scripts/audit-personal-os-discipline-gate.sh" >/tmp/solo-discipline-$$.log 2>&1; then
    discipline_ok=true
    checks_passed=$((checks_passed + 1))
  fi
else
  discipline_ok=false
fi

readiness_pct=$((checks_passed * 100 / checks_total))
if [[ "$discipline_ok" != true ]]; then
  readiness_status="partial"
  if [[ "$readiness_pct" -ge 85 ]]; then
    readiness_pct=84
  fi
elif [[ "$readiness_pct" -ge 89 ]]; then
  readiness_status="ready"
elif [[ "$readiness_pct" -ge 50 ]]; then
  readiness_status="partial"
else
  readiness_status="blocked"
fi

cat >"$JSON_OUT" <<EOF
{
  "timestamp_utc": "${STAMP}",
  "hive_base": "${HIVE_BASE}",
  "readiness": {
    "status": "${readiness_status}",
    "score_pct": ${readiness_pct},
    "checks_passed": ${checks_passed},
    "checks_total": ${checks_total},
    "discipline_gate_pass": ${discipline_ok},
    "note": "score capped at partial until audit-personal-os-discipline-gate.sh PASS (ST1)"
  },
  "solo_mode": {
    "enabled": ${solo_mode},
    "operator_email": "${operator_email}",
    "active_dashboard_accounts": ${active_accounts:-0},
    "extra_active_accounts": ${extra_accounts:-0}
  },
  "personal_os_mode": {
    "enabled": ${personal_os_mode},
    "expected_revenue_widgets_off": $([[ "$personal_os_mode" == true ]] && echo true || echo false)
  },
  "llm_keys": {
    "any_configured": ${llm_any},
    "grok": ${llm_grok},
    "anthropic": ${llm_anthropic},
    "openai": ${llm_openai},
    "tenant_build_allowed": ${llm_tenant_build_allowed},
    "tenant_source": "${llm_tenant_source}"
  },
  "optional_modules": {
    "matrix_enabled_count": ${enabled_count},
    "matrix_expected": 9,
    "missing": "${missing_modules%,}",
    "platform_overrides": ${PLATFORM_OVERRIDES_JSON}
  },
  "optional_env": {
    "forager_intelligence_loop": ${env_forager},
    "simulations": ${env_simulations},
    "lsp_mcp_bridge": ${env_lsp},
    "rubric_templates": ${env_rubric},
    "episodic_memory": ${env_episodic},
    "slack_harness_trainer": ${env_slack_trainer}
  },
  "core_solo_features": {
    "dump_sleep": true,
    "auto_graphify": true,
    "selective_recall": true,
    "execution_studio": true,
    "note": "Forced ON in solo_mode.py SOLO_CORE_FEATURES"
  },
  "pending_operator": $(echo "$PENDING_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in ['harness','monitoring','automated'] if k in d}))" 2>/dev/null || echo '{}'),
  "next_automation_steps": [
    {"priority": "P0", "task": "LLM keys in Settings → LLM keys", "done": ${llm_any}},
    {"priority": "P1", "task": "Enable optional modules", "done": $([[ "$enabled_count" -ge 9 ]] && echo true || echo false), "command": "./scripts/operator-solo-enable-modules.sh"},
    {"priority": "P1", "task": "GitHub webhook + Queen Maintainer", "command": "./scripts/operator-github-webhook-prep.sh"},
    {"priority": "P1", "task": "Forager daily cron (env + beat)", "done": ${env_forager}},
    {"priority": "P1", "task": "Ops cron suite", "command": "APPLY=1 ./scripts/install-ops-automation-cron.sh"},
    {"priority": "P2", "task": "Slack Alertmanager", "command": "./scripts/alertmanager-smoke.sh"},
    {"priority": "P3", "task": "Pattern router LLM flag", "note": "supervisor_pattern_router_llm_enabled=false default"},
    {"priority": "P3", "task": "Quarterly HA/DR drill", "command": "./scripts/dr-drill.sh"}
  ],
  "skipped_for_solo": ["team_rbac", "enterprise_workspace", "accounts_admin"],
  "report_file": "$(basename "${JSON_OUT}")"
}
EOF

cat "$JSON_OUT"
