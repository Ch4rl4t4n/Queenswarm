#!/usr/bin/env bash
# Finish Virtual Company simulate path (no Notion/Gmail tokens required).
#
# Usage:
#   ./scripts/operator-vc-finish-simulate.sh
#   APPLY=1 ./scripts/operator-vc-finish-simulate.sh   # idempotent apply + verify
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

APPLY="${APPLY:-1}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/vc-simulate-complete-${STAMP}.json"

mkdir -p "$REPORT_DIR"

echo "== Virtual Company — finish simulate path =="
echo "hive: ${HIVE_BASE} apply: ${APPLY}"
echo

if [[ "$APPLY" == "1" ]]; then
  APPLY=1 "${ROOT}/scripts/operator-virtual-company-bootstrap.sh" 2>&1 | tail -5
  echo
  APPLY=1 "${ROOT}/scripts/operator-vc-manual-tokens.sh" 2>&1 | tail -6 || true
  echo
  "${ROOT}/scripts/operator-save-vc-playbooks.sh" 2>&1 || true
  echo
fi

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"
curl -sk -H "Authorization: Bearer ${TOKEN}" \
  "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" | tee "$JSON_OUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
c = d.get('checklist', {})
fr = c.get('first_run', {})
complete = d.get('simulate_path_complete') or c.get('simulate_path_complete', False)
print('== Virtual Company simulate path ==')
print(f\"Simulate complete: {'yes' if complete else 'no'}\")
print(f\"Readiness:         {d.get('readiness_score', 0)}% (connectors add +19% max)\")
print(f\"Playbooks:         {fr.get('completed_count', 0)}/{fr.get('playbooks_total', 6)} simulate\")
print(f\"Dept swarms:       {c.get('swarms', {}).get('departments_built', 0)}/{c.get('swarms', {}).get('departments_total', 6)}\")
print(f\"Super routers:     {c.get('super_routers', {}).get('active', 0)}/{c.get('super_routers', {}).get('provisioned_total', 2)} active\")
print()
blockers = d.get('blockers') or c.get('blockers') or []
optional = d.get('optional_next_steps') or c.get('optional_next_steps') or []
if blockers:
    print('Blockers:')
    for b in blockers:
        print(f'  • {b}')
    print()
if complete:
    print('Status: Simulate path COMPLETE — run department swarms in simulate mode.')
    print('Live connectors deferred until you are ready.')
    print()
if optional:
    print('When ready (optional):')
    for o in optional:
        print(f'  • {o}')
elif not complete:
    print('Run: APPLY=1 ./scripts/operator-vc-finish-simulate.sh')
sys.exit(0 if complete and not blockers else 1)
"

echo
echo "Report: ${JSON_OUT}"
echo "UI:     ${HIVE_BASE}/integrations?tab=studio"
