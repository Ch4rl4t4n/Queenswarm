#!/usr/bin/env bash
# One-glance solo operator platform status (read-only).
#
# Usage:
#   ./scripts/operator-solo-status.sh
#   ./scripts/operator-solo-status.sh --json
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

JSON=false
[[ "${1:-}" == "--json" ]] && JSON=true

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

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

slack_env=false
[[ -n "$(load_kv .env.prod SLACK_WEBHOOK_URL || true)" ]] && slack_env=true
solo_mode=false
[[ "$(load_kv .env.prod SOLO_MODE_ENABLED || true)" =~ ^(1|true|yes|on)$ ]] && solo_mode=true

health_ok=false
curl -sf "${HIVE_BASE}/health" >/dev/null 2>&1 && health_ok=true

JWT=""
if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  JWT="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
fi

vc_readiness=0
vc_simulate=false
life_os=false
if [[ -n "${JWT// }" ]]; then
  audit="$(curl -sk -H "Authorization: Bearer ${JWT}" "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" 2>/dev/null || echo '{}')"
  vc_readiness="$(echo "$audit" | python3 -c "import json,sys; print(json.load(sys.stdin).get('readiness_score',0))" 2>/dev/null || echo 0)"
  vc_simulate="$(echo "$audit" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('checklist',{}).get('simulate_path_complete',False)).lower())" 2>/dev/null || echo false)"
  life_os="$(echo "$audit" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('checklist',{}).get('first_run',{}).get('life_os_first_run_completed',False)).lower())" 2>/dev/null || echo false)"
fi

routines=0
dump_available=false
episodic_total=0
if [[ -n "${JWT// }" ]]; then
  routines="$(curl -sk -H "Authorization: Bearer ${JWT}" "${HIVE_BASE}/api/v1/agents/routines" 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)"
  dump_available="$(curl -sk -H "Authorization: Bearer ${JWT}" "${HIVE_BASE}/api/v1/dump-sleep/overnight-report" 2>/dev/null | python3 -c "import json,sys; print(str(json.load(sys.stdin).get('available',False)).lower())" 2>/dev/null || echo false)"
  episodic_total="$(curl -sk -H "Authorization: Bearer ${JWT}" "${HIVE_BASE}/api/v1/memory/episodic/summary" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('total_items',0))" 2>/dev/null || echo 0)"
fi

if "$JSON"; then
  python3 - <<PY
import json
print(json.dumps({
  "timestamp_utc": "${STAMP}",
  "hive_base": "${HIVE_BASE}",
  "solo_mode": ${solo_mode},
  "health_ok": ${health_ok},
  "vc_readiness": ${vc_readiness},
  "simulate_path_complete": ${vc_simulate} == "true",
  "life_os_first_run": ${life_os} == "true",
  "routines_active": ${routines},
  "dump_sleep_report": ${dump_available} == "true",
  "episodic_items": ${episodic_total},
  "slack_webhook": ${slack_env},
}, indent=2))
PY
  exit 0
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Solo — platform status                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "time: ${STAMP}  hive: ${HIVE_BASE}"
echo

echo "── Core ──"
echo "  Health:              $([[ "$health_ok" == true ]] && echo '✓ OK' || echo '✗ FAIL')"
echo "  Solo mode:           $([[ "$solo_mode" == true ]] && echo 'ON (multi-tenant B2B hidden; revenue ON)' || echo 'OFF')"
echo "  VC readiness:        ${vc_readiness}%"
echo "  Simulate path:       $([[ "$vc_simulate" == true ]] && echo '✓ complete' || echo '○ pending')"
echo "  Life OS first-run:   $([[ "$life_os" == true ]] && echo '✓ done' || echo '○ pending')"
echo

echo "── Automation ──"
echo "  Cron routines:       ${routines} active"
echo "  Dump & Sleep report: $([[ "$dump_available" == true ]] && echo '✓ available' || echo '○ none yet')"
echo "  Episodic memory:     ${episodic_total} items"
echo

echo "── Integrations / alerts ──"
echo "  Slack webhook:       $([[ "$slack_env" == true ]] && echo '✓ set' || echo '○ empty (alerts → blackhole)')"
echo "  Commercial checkout: REMOVED — not in current roadmap scope"
echo

echo "── Queen policy (operator-editable) ──"
curated_chars="—"
if [[ -n "${JWT// }" ]]; then
  curated_chars="$(
    curl -sk -H "Authorization: Bearer ${JWT}" "${HIVE_BASE}/api/v1/memory/curated" 2>/dev/null \
      | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('—'); sys.exit(0)
parts = [f\"{k[:4]}={len(v or '')}\" for k, v in d.items()]
print(' '.join(parts))
" 2>/dev/null || echo '—'
  )"
fi
echo "  Curated memory:      ${curated_chars}  (UI: Settings → AI · harness → Curated memory)"
echo "  Orchestrator prompt: UI → /swarms → 'Edit Orchestrator prompt' (top cyan card)"
echo "  Manager prompts:     UI → /swarms → row action 'Edit policy'"
echo "  Worker prompts:      UI → click any bee hex card → Full editor"
echo
echo "  Seed/reset defaults: ./scripts/operator-hive-policy-seed.sh [--force]"
echo

echo "── Evening loop (operator) ──"
echo "  1. Ballroom → Dump & Sleep (upload .md + voice note)"
echo "  2. Morning → Dreaming / Overnight report"
echo "  3. Knowledge → Episodic Memory timeline"
echo "  4. Life OS routine fires daily 06:00 UTC"
echo
echo "Next: ./scripts/operator-full-app-audit.sh  (API smoke + UI checklist)"
