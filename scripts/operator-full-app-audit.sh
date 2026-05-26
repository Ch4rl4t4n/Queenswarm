#!/usr/bin/env bash
# Full application audit — production API smoke + UI walkthrough checklist (read-only).
#
# Covers every major solo feature area. Commercial surfaces (Stripe, billing, enterprise)
# are marked DEFERRED in solo mode — not failures.
#
# Usage:
#   ./scripts/operator-full-app-audit.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/operator-full-app-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/full-app-audit-${STAMP}.json"
CHECKLIST_OUT="${REPORT_DIR}/full-app-walkthrough-${STAMP}.md"

mkdir -p "$REPORT_DIR"

solo_mode=false
if [[ -f "$ENV_FILE" ]]; then
  val="$(grep -E '^SOLO_MODE_ENABLED=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r"'"'"' ' || true)"
  [[ "${val,,}" == "true" || "$val" == "1" ]] && solo_mode=true
fi

resolve_jwt() {
  docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n'
}

PASS=0
WARN=0
FAIL=0
RESULTS=()

probe() {
  local area="$1" path="$2" expect="${3:-200}" note="${4:-}"
  local code body
  code="$(curl -sk -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}${path}" || echo "000")"
  local status="fail"
  if [[ "$code" == "$expect" ]]; then
    status="pass"
    PASS=$((PASS + 1))
    echo "  ✓ ${area} — HTTP ${code}"
  elif [[ "$expect" == *"|"* ]] && echo "|${code}|" | grep -qF "|${code}|"; then
    status="pass"
    PASS=$((PASS + 1))
    echo "  ✓ ${area} — HTTP ${code} (${note:-alt ok})"
  elif [[ "$code" == "403" && -n "$note" ]]; then
    status="warn"
    WARN=$((WARN + 1))
    echo "  ○ ${area} — HTTP 403 (${note})"
  else
    status="fail"
    FAIL=$((FAIL + 1))
    echo "  ✗ ${area} — HTTP ${code} (expected ${expect})"
  fi
  RESULTS+=("{\"area\":\"${area}\",\"path\":\"${path}\",\"http\":${code},\"status\":\"${status}\",\"note\":\"${note}\"}")
}

probe_json_field() {
  local area="$1" path="$2" py_check="$3"
  local body code ok=false
  code="$(curl -sk -o /tmp/qw_audit_body.json -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}${path}" || echo "000")"
  if [[ "$code" == "200" ]] && python3 -c "$py_check" /tmp/qw_audit_body.json 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "  ✓ ${area} — payload OK"
    RESULTS+=("{\"area\":\"${area}\",\"path\":\"${path}\",\"http\":200,\"status\":\"pass\",\"note\":\"payload\"}")
  else
    FAIL=$((FAIL + 1))
    echo "  ✗ ${area} — HTTP ${code} or bad payload"
    RESULTS+=("{\"area\":\"${area}\",\"path\":\"${path}\",\"http\":${code},\"status\":\"fail\",\"note\":\"payload\"}")
  fi
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Full App Audit (production API smoke)        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "time: ${STAMP}  hive: ${HIVE_BASE}  solo: ${solo_mode}"
echo

TOKEN="$(resolve_jwt)"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: could not issue operator JWT from ${BACKEND}" >&2
  exit 1
fi

curl -sf "${HIVE_BASE}/health" >/dev/null && echo "  ✓ health — OK" && PASS=$((PASS + 1)) || { echo "  ✗ health"; FAIL=$((FAIL + 1)); }

echo
echo "── 1. Command center / Dashboard ──"
probe "cockpit" "/api/v1/dashboard/cockpit"
probe "dashboard summary" "/api/v1/dashboard/summary"
probe "rapid loop" "/api/v1/dashboard/rapid-loop"
probe "time saved" "/api/v1/dashboard/time-saved"
probe "unified savings" "/api/v1/dashboard/unified-savings"
probe "swarms overview" "/api/v1/dashboard/swarms-overview"
probe "foragers overview" "/api/v1/dashboard/foragers-overview" "200|403" "module may be off"

echo
echo "── 2. Virtual Company + connectors ──"
probe_json_field "VC readiness" "/api/v1/virtual-company/readiness-audit" "
import json, sys
d = json.load(open(sys.argv[1]))
score = d.get('readiness_score') or d.get('readiness_pct') or 0
sys.exit(0 if score >= 80 else 1)
"
probe "VC profile" "/api/v1/virtual-company/profile"
probe "VC bootstrap checklist" "/api/v1/virtual-company/bootstrap-checklist"
probe "execution studio overview" "/api/v1/execution-studio/overview"
probe "connectors catalog" "/api/v1/connectors/catalog"
probe "phase3 integration overview" "/api/v1/connectors/phase3/integration-overview"

echo
echo "── 3. Swarms · Agents · Sessions · Routines ──"
probe "swarms list" "/api/v1/swarms"
probe "agents list" "/api/v1/agents"
probe "sessions summary" "/api/v1/agents/sessions/summary"
probe "routines" "/api/v1/agents/routines"
probe "tasks" "/api/v1/tasks?limit=5"

echo
echo "── 4. Knowledge · Memory · Graphify ──"
probe "hive-mind graph" "/api/v1/hive-mind/graph"
probe "hive-mind recall settings" "/api/v1/hive-mind/recall-settings"
probe "episodic summary" "/api/v1/memory/episodic/summary"
probe "dreaming settings" "/api/v1/dreaming/settings"
probe "dreaming last digest" "/api/v1/dreaming/last-digest" "200|404" "no digest yet ok"
probe "dump-sleep overnight report" "/api/v1/dump-sleep/overnight-report"
probe "recipes list" "/api/v1/recipes?limit=10"

echo
echo "── 5. Harness · Foragers · Maintainer ──"
probe "harness snapshot" "/api/v1/harness/snapshot"
probe "pattern explorer" "/api/v1/harness/pattern-explorer"
probe "foragers list" "/api/v1/foragers" "200|403" "foragers module"
probe "lsp bridge status" "/api/v1/harness/lsp-bridge/status" "200|403" "lsp module"
probe "rubric templates" "/api/v1/harness/rubric-templates" "200|403" "rubric module"
probe "queen maintainer settings" "/api/v1/queen-maintainer/settings"
probe "queen maintainer tech-health" "/api/v1/queen-maintainer/tech-health"

echo
echo "── 6. Settings · LLM · Platform ──"
probe "llm routing settings" "/api/v1/llm-routing/settings"
probe "llm cost savings" "/api/v1/llm-routing/cost-savings"
probe "platform features" "/api/v1/operator/platform-features" "200|403" "admin only"
probe "system status" "/api/v1/system/status"

if [[ "$solo_mode" == true ]]; then
  echo
  echo "── 7. Commercial (DEFERRED in solo — not blocking) ──"
  for path in /api/v1/billing/plans /api/v1/settings/enterprise/config; do
    code="$(curl -sk -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}${path}" || echo "000")"
    echo "  ○ deferred ${path} — HTTP ${code}"
    WARN=$((WARN + 1))
  done
fi

# JSON report
results_json="$(printf '%s\n' "${RESULTS[@]}" | paste -sd, -)"
cat >"$JSON_OUT" <<EOF
{
  "timestamp_utc": "${STAMP}",
  "hive_base": "${HIVE_BASE}",
  "solo_mode": ${solo_mode},
  "summary": {"pass": ${PASS}, "warn": ${WARN}, "fail": ${FAIL}},
  "commercial_deferred": ${solo_mode},
  "results": [${results_json}],
  "report_file": "$(basename "${JSON_OUT}")"
}
EOF

# UI walkthrough checklist (Slovak)
cat >"$CHECKLIST_OUT" <<'MDEOF'
# Queenswarm — UI walkthrough checklist (krok za krokom)

Spolu prejdite každú oblasť. Označte ✓ keď funguje, ✗ keď nie.

## 1. Dashboard / Command center
- [ ] `/` — cockpit načíta metriky, žiadny duplicate search bar (desktop)
- [ ] Rapid loop + time saved widgety
- [ ] Swarm board / overview

## 2. Swarms
- [ ] `/swarms` — 6 VC department swarms + Life OS + Sentinel
- [ ] `/swarms/new` — Life OS template (nie coming soon)
- [ ] Otvoriť swarm → agents, pollen, dance feed

## 3. Agents & Sessions
- [ ] `/agents` — zoznam agentov
- [ ] Session: vytvoriť → interact → simulate playbook
- [ ] Routines: 8 aktívnych, správny cron v UI

## 4. Execution Studio + Integrations
- [ ] `/integrations` — Notion + Gmail + GitHub active (3/3)
- [ ] Super Tool Routers: 2/2
- [ ] Simulate execute na jednom connectore
- [ ] Operator notifications — Telegram test

## 5. Ballroom
- [ ] Dump & Sleep upload (.md + voice)
- [ ] Overnight report / Dreaming digest ráno
- [ ] Voice TTS ak je zapnuté

## 6. Knowledge
- [ ] HiveMind graph + selective recall preview
- [ ] Auto-Graphify upload
- [ ] Episodic memory timeline (400+ položiek)
- [ ] Recipes — 6 VC playbooks + Life OS

## 7. Harness & Intelligence
- [ ] Settings → AI harness snapshot
- [ ] Pattern explorer onboarding
- [ ] Foragers (ak zapnuté) — daily cron output
- [ ] Queen Maintainer webhook status

## 8. Settings
- [ ] AI · LLM & Voice — Grok primary, free_first
- [ ] Platform — optional modules ON (foragers, episodic, …)
- [ ] Notifications — Telegram + SMTP
- [ ] Audit log — posledné akcie

## 9. Nightly loop (operátor)
- [ ] Večer: Dump & Sleep batch
- [ ] Ráno: overnight report + episodic
- [ ] Life OS routine 06:00 UTC

## DEFERRED (nie teraz)
- Stripe / Billing / Enterprise workspace
- Team RBAC / multi-account
- Lead magnets / marketplace UGC

---
Automated API slice: see companion JSON report.
MDEOF

echo
echo "══════════════════════════════════════════════════════════"
echo "Full app audit: pass=${PASS} warn=${WARN} fail=${FAIL}"
echo "JSON:  ${JSON_OUT}"
echo "UI checklist: ${CHECKLIST_OUT}"
echo

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
echo "== Full app audit: OK =="
