#!/usr/bin/env bash
# Personal OS weekly verify — all POS gates + prod flags + API smoke (read-only).
#
# Usage:
#   ./scripts/operator-personal-os-verify.sh
#   SKIP_PROD=1 ./scripts/operator-personal-os-verify.sh   # local gates only
#   HIVE_BASE=https://queenswarm.love ./scripts/operator-personal-os-verify.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-queenswarm_prod-backend-1}"
SKIP_PROD="${SKIP_PROD:-0}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/personal-os-verify-${STAMP}.json"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

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
  local key="$1" expected="${2:-true}"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  val="${val,,}"
  if [[ "$expected" == "true" ]]; then
    [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]
  else
    [[ "$val" == "false" || "$val" == "0" || "$val" == "no" || -z "$val" ]]
  fi
}

mkdir -p "$REPORT_DIR"

echo "=== Personal OS Weekly Verify ==="
echo "stamp: ${STAMP}"
echo ""

echo "--- Local POS gates ---"
GATES=(
  "audit-personal-os-gate.sh"
  "audit-life-os-gate.sh"
  "audit-autopilot-gate.sh"
  "audit-skill-factory-lite-gate.sh"
  "audit-marketing-team-gate.sh"
  "audit-faceless-pipeline-gate.sh"
  "audit-jarvis-intelligence-gate.sh"
  "audit-codebase-memory-mcp-gate.sh"
  "audit-research-bee-gate.sh"
  "audit-personal-os-compound-gate.sh"
  "audit-personal-os-adoption-gate.sh"
  "audit-personal-os-daily-flow-gate.sh"
  "audit-personal-os-memory-adoption-gate.sh"
  "audit-personal-os-second-brain-adoption-gate.sh"
  "audit-personal-os-agent-loop-adoption-gate.sh"
  "audit-personal-os-closed-loop-verify-gate.sh"
  "audit-personal-os-intel-adoption-gate.sh"
  "audit-personal-os-social-intel-adoption-gate.sh"
  "audit-personal-os-data-monitor-adoption-gate.sh"
  "audit-personal-os-discovery-adoption-gate.sh"
  "audit-personal-os-learn-rail-adoption-gate.sh"
  "audit-personal-os-harness-adoption-gate.sh"
  "audit-personal-os-smart-rebuild-adoption-gate.sh"
  "audit-personal-os-export-harness-adoption-gate.sh"
  "audit-personal-os-export-channels-adoption-gate.sh"
  "audit-second-brain-gate.sh"
  "audit-memory-project-tags-gate.sh"
  "audit-personal-os-dead-code-gate.sh"
  "audit-solo-daily-plan-gate.sh"
  "audit-publish-queue-gate.sh"
  "audit-social-publish-gate.sh"
)
for gate in "${GATES[@]}"; do
  if [[ -x "${ROOT}/scripts/${gate}" ]]; then
    extra_env=()
    if [[ "$gate" == "audit-personal-os-gate.sh" ]]; then
      extra_env=(RUN_PERSONAL_OS_TESTS=1)
    fi
    if env "${extra_env[@]}" "${ROOT}/scripts/${gate}" >/tmp/personal-os-gate-$$.log 2>&1; then
      pass "$gate"
    else
      fail "$gate (see /tmp/personal-os-gate-$$.log)"
    fi
  else
    fail "missing script ${gate}"
  fi
done

echo ""
echo "--- Env file flags (${ENV_FILE}) ---"
for pair in \
  "SOLO_MODE_ENABLED:true" \
  "PERSONAL_OS_MODE_ENABLED:true" \
  "ROUTINES_ENABLED:true" \
  "REVENUE_FUNNEL_MISSION_HOME_ENABLED:false" \
  "CATALOG_WAVE_MISSION_HOME_ENABLED:false" \
  "FACTORY_LAUNCH_MISSION_HOME_ENABLED:false" \
  "TRADING_COCKPIT_ENABLED:false"; do
  key="${pair%%:*}"
  expected="${pair##*:}"
  if check_bool_env "$key" "$expected"; then
    pass "${key}=${expected}"
  else
    fail "${key} expected ${expected}"
  fi
done

if [[ "$SKIP_PROD" == "1" ]]; then
  echo ""
  echo "SKIP_PROD=1 — skipping live prod probes"
else
  echo ""
  echo "--- Prod health (${HIVE_BASE}) ---"
  for path in /health /api/v1/health /health/ready; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}${path}" || echo 000)"
    if [[ "$code" == "200" ]]; then
      pass "${path} → ${code}"
    else
      fail "${path} → ${code}"
    fi
  done

  echo ""
  echo "--- Runtime settings (docker) ---"
  if docker ps --format '{{.Names}}' | grep -qx "$BACKEND_CONTAINER"; then
    SETTINGS_OUT="$(docker exec "$BACKEND_CONTAINER" python -c "
from app.core.config import settings
checks = {
  'solo_mode_enabled': settings.solo_mode_enabled,
  'personal_os_mode_enabled': settings.personal_os_mode_enabled,
  'routines_enabled': settings.routines_enabled,
  'revenue_funnel_mission_home_enabled': settings.revenue_funnel_mission_home_enabled,
  'trading_cockpit_enabled': settings.trading_cockpit_enabled,
  'calendar_daily_planner_enabled': settings.calendar_daily_planner_enabled,
  'marketing_team_enabled': getattr(settings, 'marketing_team_enabled', False),
  'faceless_content_pipeline_enabled': getattr(settings, 'faceless_content_pipeline_enabled', False),
}
for k, v in checks.items():
    print(f'{k}={v}')
" 2>/dev/null || true)"
    if [[ -n "$SETTINGS_OUT" ]]; then
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        pass "runtime ${line}"
      done <<<"$SETTINGS_OUT"
      if ! grep -q 'personal_os_mode_enabled=True' <<<"$SETTINGS_OUT"; then
        fail "runtime personal_os_mode_enabled not True"
      fi
    else
      fail "could not read runtime settings from ${BACKEND_CONTAINER}"
    fi
  else
    fail "backend container ${BACKEND_CONTAINER} not running"
  fi

  echo ""
  echo "--- API routes (JWT smoke) ---"
  TOKEN="$(docker exec "$BACKEND_CONTAINER" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "${TOKEN// }" ]]; then
    for path in \
      "/api/v1/solo-operator/mission-home" \
      "/api/v1/operator/marketing-team" \
      "/api/v1/operator/faceless-pipeline" \
      "/api/v1/solo-operator/trio" \
      "/api/v1/solo-operator/four-lanes" \
      "/api/v1/skill-factory/snapshot"; do
      code="$(curl -sS -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer ${TOKEN}" \
        "${HIVE_BASE}${path}" || echo 000)"
      if [[ "$code" == "200" ]]; then
        pass "${path} → ${code}"
      else
        fail "${path} → ${code}"
      fi
    done
    COMMERCIAL="$(curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/skill-factory/snapshot" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print('false' if d.get('commercial_launch_enabled') is False else 'true')" 2>/dev/null || echo unknown)"
    if [[ "$COMMERCIAL" == "false" ]]; then
      pass "skill-factory commercial_launch_enabled=false"
    else
      fail "skill-factory commercial_launch_enabled expected false (got ${COMMERCIAL})"
    fi
  else
    fail "operator JWT unavailable — skip API smoke"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  STATUS="pass"
  echo "PERSONAL OS VERIFY: PASS"
else
  STATUS="fail"
  echo "PERSONAL OS VERIFY: FAIL (${FAIL} checks)"
fi

python3 - <<PY
import json, datetime
out = {
  "stamp": "${STAMP}",
  "status": "${STATUS}",
  "fail_count": ${FAIL},
  "hive_base": "${HIVE_BASE}",
  "skip_prod": ${SKIP_PROD},
}
with open("${JSON_OUT}", "w") as f:
    json.dump(out, f, indent=2)
print(f"report: ${JSON_OUT}")
PY

exit "$FAIL"
